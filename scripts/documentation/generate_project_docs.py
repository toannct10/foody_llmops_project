"""Build Vietnamese study/report DOCX from frozen evidence without runtime imports.

Run with the Codex document-generation Python runtime, not the application venv.
Input CSV/JSON/MD/PNG files are read only. Outputs are restricted to docs/ and QA temp.
"""

import csv
import json
import math
import re
import statistics
from pathlib import Path

from content_vi import CHAPTERS, REPORT_TITLES
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image
from reference_vi import CONTRADICTIONS, EXTERNAL, PARAMETERS, QUESTIONS, WALKTHROUGHS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs"
QA = ROOT / "scripts" / "documentation" / ".qa"
DATE = "22/10/2026"
SECTIONS = {}
for part in CHAPTERS.split("@@")[1:]:
    first, body = part.split("\n", 1)
    n, title = first.split("|", 1)
    SECTIONS[int(n)] = (title, body.strip())


def j(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def rows(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fmt(value):
    if value is None or value == "":
        return "N/A"
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).replace("|", "/").replace("\n", "; ")


class Text:
    def __init__(self):
        self.parts = []
        self.tables = 0
        self.figures = 0

    def add(self, text):
        self.parts.append(text.strip())

    def table(self, title, headers, data, source, kind="MEASURED"):
        self.tables += 1
        self.add(f"Bảng {self.tables}. {title}")
        self.add(
            "| "
            + " | ".join(headers)
            + " |\n| "
            + " | ".join("---" for _ in headers)
            + " |\n"
            + "\n".join("| " + " | ".join(fmt(v) for v in row) + " |" for row in data)
        )
        self.add(f"Nguồn: {source}. Loại: {kind}.")

    def csv(self, path, columns, labels=None, title=None, kind="MEASURED"):
        self.table(
            title or Path(path).stem,
            labels or columns,
            [[numeric(row.get(key, "")) for key in columns] for row in rows(path)],
            path,
            kind,
        )

    def figure(self, path, caption, caveat=""):
        if not (ROOT / path).is_file():
            raise FileNotFoundError(path)
        self.figures += 1
        self.add(f"![{caption}](../{path})")
        self.add(f"Hình {self.figures}. {caption}. Nguồn: {path}. {caveat}")

    def value(self):
        return "\n\n".join(self.parts) + "\n"


def numeric(value):
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError):
        return value


def facts():
    d = j("reports/food_dataset_report.json")
    split = j("data/food/splits/metadata.json")
    foody = j("reports/foody_intelligence/cleaning.json")
    token = j("reports/task2/rag_token_statistics.json")
    result = [
        (
            "Research source rows",
            d["raw_rows"],
            "MEASURED",
            "reports/food_dataset_report.json",
            "Có đối chiếu metadata",
            "Có",
            "Toàn nguồn đa ngôn ngữ",
        ),
        (
            "Vietnamese restaurant rows",
            d["valid_rows"],
            "MEASURED",
            "reports/food_dataset_report.json",
            "Có",
            "Có",
            "Đơn vị sentence/aspect",
        ),
        (
            "Review IDs",
            d["unique_reviews"],
            "MEASURED",
            "reports/food_dataset_report.json",
            "Metadata đối chiếu",
            "Có",
            "Không bằng rows",
        ),
        (
            "Normalized texts",
            d["unique_sentences"],
            "MEASURED",
            "reports/food_dataset_report.json",
            "3768+751+797",
            "Có",
            "Aspect group count",
        ),
        (
            "Sentiment distribution",
            d["sentiment_counts"],
            "MEASURED",
            "reports/task2/class_distribution.csv",
            "Tổng 5869",
            "Có",
            "Class counts không đổi bởi weighting",
        ),
        (
            "Imbalance ratio",
            3714 / 294,
            "DERIVED",
            "reports/task2/class_distribution.csv",
            "Có",
            "Có",
            "majority/minority",
        ),
        (
            "Split rows",
            split["counts"],
            "MEASURED",
            "data/food/splits/metadata.json",
            "Tổng 5869",
            "Có",
            "Seed42",
        ),
        (
            "Leakage checks",
            split["leakage_checks"],
            "MEASURED",
            "data/food/splits/metadata.json",
            "Không resplit",
            "Có",
            "Không đảm bảo near duplicates",
        ),
        (
            "Split SHA256",
            split["split_file_sha256"],
            "MEASURED",
            "data/food/splits/metadata.json",
            "Checksum audit",
            "Có",
            "Giữ frozen input",
        ),
        (
            "Foody raw rows",
            foody["raw_rows"],
            "MEASURED",
            "reports/foody_intelligence/cleaning.json",
            "33938+8",
            "Có",
            "Mọi source row được giữ",
        ),
        (
            "Foody valid rows",
            foody["valid_ai_rows"],
            "MEASURED",
            "reports/foody_intelligence/cleaning.json",
            "33946−8",
            "Có",
            "Không phải 31694",
        ),
        (
            "Foody inference observations",
            foody["deduplicated_ai_observations"],
            "MEASURED",
            "reports/foody_intelligence/cleaning.json",
            "Không rerun inference",
            "Có",
            "Restaurant key + normalized text",
        ),
        (
            "Foody distinct valid reviews",
            foody["distinct_valid_review_ids"],
            "MEASURED",
            "reports/foody_intelligence/cleaning.json",
            "Đối chiếu manifest",
            "Có",
            "RAG documents",
        ),
        (
            "Foody restaurants",
            foody["restaurant_count"],
            "MEASURED",
            "reports/foody_intelligence/cleaning.json",
            "Không fuzzy merge",
            "Có",
            "Name-derived identity",
        ),
    ]
    for name, path in [
        ("Rule", "reports/baselines/rule_based_test_metrics.json"),
        ("TF-IDF", "reports/baselines/tfidf_test_metrics.json"),
        ("Qwen V1", "reports/proposed_v1/qwen_test_metrics.json"),
        ("Qwen V2-A", "reports/proposed_v2/test_metrics.json"),
    ]:
        m = j(path)
        result.append(
            (
                name + " test macro-F1",
                m["macro_f1"],
                "MEASURED",
                path,
                "Confusion recalculated" if name in {"Rule", "TF-IDF"} else "Saved result",
                "Có",
                "Exploratory" if name == "Qwen V2-A" else "Frozen text-only",
            )
        )
    result += [
        (
            "Three-seed test macro-F1",
            "0.682854 ± 0 (sample SD)",
            "DERIVED",
            "reports/task2/baseline_three_seed.csv",
            "Có",
            "Có",
            "Cùng membership",
        ),
        (
            "Aspect micro/macro F1",
            "0.832276657 / 0.633628001",
            "MEASURED",
            "reports/aspect_classifier/test_metrics.json",
            "Per-class đối chiếu",
            "Có",
            "797 groups; room/amenities support0",
        ),
        (
            "RAG documents/vectors/BM25",
            "32457 / 32457 / 32457",
            "MEASURED",
            "reports/task2/DOCKER_ACCEPTANCE.md",
            "Manifests audit",
            "Có",
            "Không rebuild",
        ),
        (
            "MiniLM corpus tokens",
            token["minilm_embedding"]["total_tokens"],
            "MEASURED",
            "reports/task2/rag_token_statistics.json",
            "Histogram sum",
            "Có",
            "No special tokens; no truncation khi đếm",
        ),
        (
            "Qwen corpus tokens",
            token["qwen2_5_3b_generation"]["total_tokens"],
            "MEASURED",
            "reports/task2/rag_token_statistics.json",
            "Histogram sum",
            "Có",
            "Vocabulary khác MiniLM",
        ),
        (
            "Embedding dimensions",
            384,
            "CONFIGURED/EXTERNAL",
            "src/rag/embeddings.py",
            "Shape check code",
            "Có",
            "Architecture-fixed",
        ),
        (
            "Embedding seconds",
            1054.633672599999,
            "MEASURED",
            "data/foody/vector_store/index_manifest.json",
            "Không re-embed",
            "Có",
            "Embedding compute sum",
        ),
        (
            "Raw vector bytes",
            32457 * 384 * 4,
            "DERIVED",
            "src/rag/embeddings.py; Chroma manifest",
            "Có",
            "Có",
            "Không phải Chroma disk",
        ),
        (
            "Dense/V2/V3 MRR",
            "0.018518519 / 0.055555556 / 0.166666667",
            "MEASURED",
            "reports/rag_v3/retrieval_policies.csv",
            "Giữ score gốc",
            "Có",
            "Incomplete positives, sáu query",
        ),
        (
            "Historical Hit@5/10 naming",
            "Actual formula = macro known-positive recall",
            "SOURCE AUDIT",
            "src/rag/evaluation.py",
            "Formula traced",
            "Có",
            "Không đổi experiment file",
        ),
        (
            "V3 accepted generator",
            "2 complete / 1 incomplete / 0 unsupported / 3 insufficient / 2 fallback",
            "MEASURED",
            "reports/rag_v3/generation_metrics.json",
            "Saved counts",
            "Có",
            "Validator-detected only",
        ),
        (
            "Three-family benchmark",
            "6 cases per model",
            "MEASURED",
            "reports/task2/llm_comparison.csv",
            "Saved rows",
            "Có",
            "Không general ranking",
        ),
        (
            "Latency and model sizes",
            "Tách từng task/run; xem bảng feasibility",
            "MEASURED",
            "reports/task2/FEASIBILITY.csv",
            "Không đo mới",
            "Có",
            "N/A giữ nguyên; DeepSeek wall-time fallback",
        ),
        (
            "Docker",
            "pipeline exit0; qwen healthy; backend/UI HTTP200",
            "MEASURED",
            "reports/task2/DOCKER_ACCEPTANCE.md",
            "Reuse acceptance",
            "Có",
            "GPU container NOT VERIFIED",
        ),
        (
            "Tests",
            "288 passed / 1 warning",
            "MEASURED",
            "reports/task2/REVIEW2_STATUS_SUMMARY_VI.md",
            "Không rerun trong docs",
            "Có",
            "KEY_NUMBERS 287 stale",
        ),
        (
            "CI",
            "39739640437 success at 4229a8b",
            "MEASURED",
            "https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39739640437",
            "Read-only API 2026-10-22",
            "Có",
            "Docs mới chưa trong run",
        ),
        (
            "CD release",
            "39742439011 success v1.0.1",
            "MEASURED",
            "https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39742439011",
            "Read-only API 2026-10-22",
            "Có",
            "Publication, không remote deployment",
        ),
        (
            "GHCR manifest",
            "sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a",
            "MEASURED",
            "ghcr.io/iamndtk1230/mllops-food_data:v1.0.1",
            "Read-only imagetools inspect",
            "Có",
            "linux/amd64",
        ),
    ]
    return result


def formulas():
    tf = j("reports/baselines/tfidf_test_metrics.json")
    cm = tf["confusion_matrix"]
    total = sum(map(sum, cm))
    vals = []
    for k in range(3):
        tp = cm[k][k]
        support = sum(cm[k])
        predicted = sum(row[k] for row in cm)
        p, r = tp / predicted, tp / support
        vals.append((p, r, 2 * p * r / (p + r), support))
    macro = statistics.mean(v[2] for v in vals)
    assert abs(macro - tf["macro_f1"]) < 1e-12
    return [
        (
            "F01",
            "Imbalance ratio",
            "IR = max(n_c) / min(n_c)",
            "3714 / 294",
            3714 / 294,
            "Lớp đông gấp 12,63 lần lớp ít",
            "reports/task2/class_distribution.csv",
            "DERIVED",
            "Không có function model; phép tính documentation",
        ),
        (
            "F02",
            "Balanced class weights",
            "w_c = N / (K × n_c)",
            "4140/(3×1307); 4140/(3×208); 4140/(3×2625)",
            "; ".join(f"{4140 / (3 * n):.9f}" for n in (1307, 208, 2625)),
            "Train-only; không đổi số mẫu",
            "reports/task2/imbalance_comparison.csv",
            "DERIVED",
            "src/baselines/tfidf_logreg.py::build_pipeline",
        ),
        (
            "F03",
            "Term frequency",
            "TF_intro = count / length; TF_project = 1 + ln(count) nếu count>0",
            "EXAMPLE count=3,length=10: 3/10; 1+ln(3)",
            f"0.3; {1 + math.log(3):.9f}",
            "Ví dụ minh họa, không phải số liệu project",
            "src/baselines/tfidf_logreg.py",
            "THEORY/EXAMPLE",
            "TfidfVectorizer(sublinear_tf=True)",
        ),
        (
            "F04",
            "Smoothed IDF",
            "IDF = ln((1+N)/(1+df)) + 1",
            "EXAMPLE N=100,df=10: ln(101/11)+1",
            math.log(101 / 11) + 1,
            "Vocabulary/IDF học train; minh họa",
            "src/baselines/tfidf_logreg.py; sklearn API",
            "THEORY/EXAMPLE",
            "TfidfVectorizer(smooth_idf=True mặc định)",
        ),
        (
            "F05",
            "TF IDF và L2",
            "u_t = TF_t × IDF_t; x = u / sqrt(Σ u_t²)",
            "EXAMPLE u=[3,4] → norm=5",
            "[0.6,0.8]",
            "Minh họa chuẩn hóa vector, không phải review embedding",
            "src/baselines/tfidf_logreg.py",
            "THEORY/EXAMPLE",
            "TfidfVectorizer(norm='l2' mặc định)",
        ),
        (
            "F06",
            "Logistic sigmoid",
            "z = wᵀx+b; σ(z)=1/(1+exp(−z))",
            "EXAMPLE z=0",
            0.5,
            "Nhị phân OVR aspect, không công thức 3-class sentiment",
            "src/foody/aspect.py",
            "THEORY/EXAMPLE",
            "OneVsRestClassifier(LogisticRegression)",
        ),
        (
            "F07",
            "Multinomial softmax",
            "p_c = exp(z_c) / Σ_j exp(z_j)",
            "EXAMPLE scores=[0,0,0]",
            "[1/3,1/3,1/3]",
            "Xác suất ba lớp cộng thành1",
            "src/baselines/tfidf_logreg.py",
            "THEORY/EXAMPLE",
            "LogisticRegression(solver='lbfgs')",
        ),
        (
            "F08",
            "Accuracy thật từ confusion",
            "accuracy = Σ diagonal / N",
            f"(228+19+471)/{total}",
            (228 + 19 + 471) / total,
            "Tính lại prediction đã lưu, không test inference mới",
            "reports/baselines/tfidf_test_metrics.json",
            "DERIVED",
            "src/baselines/metrics.py::scores → accuracy_score",
        ),
        (
            "F09",
            "Neutral precision",
            "P = TP/(TP+FP)",
            "19/(9+19+21)",
            vals[1][0],
            "49 predicted-neutral, 19 đúng",
            "reports/baselines/tfidf_test_metrics.json",
            "DERIVED",
            "src/baselines/metrics.py::class_report",
        ),
        (
            "F10",
            "Neutral recall",
            "R = TP/(TP+FN)",
            "19/(10+19+14)",
            vals[1][1],
            "Tìm được19 trong43 gold-neutral",
            "reports/baselines/tfidf_test_metrics.json",
            "DERIVED",
            "precision_recall_fscore_support",
        ),
        (
            "F11",
            "Neutral F1",
            "F1 = 2PR/(P+R) = 2TP/(2TP+FP+FN)",
            "38/(38+30+24)",
            vals[1][2],
            "Trade-off precision/recall",
            "reports/baselines/tfidf_test_metrics.json",
            "DERIVED",
            "src/baselines/metrics.py::scores",
        ),
        (
            "F12",
            "Macro F1",
            "macro-F1 = (Σ_c F1_c)/K",
            "(0.7728813559322034+0.4130434782608696+0.8626373626373627)/3",
            macro,
            "Mỗi lớp cùng trọng số",
            "reports/baselines/tfidf_test_metrics.json",
            "DERIVED",
            "precision_recall_fscore_support(average='macro')",
        ),
        (
            "F13",
            "Weighted F1",
            "weighted-F1 = Σ support_c×F1_c / N",
            "(284×F1_negative+43×F1_neutral+560×F1_positive)/887",
            sum(v[2] * v[3] for v in vals) / total,
            "Lớp đông ảnh hưởng lớn",
            "reports/baselines/tfidf_test_metrics.json",
            "DERIVED",
            "precision_recall_fscore_support(average='weighted')",
        ),
        (
            "F14",
            "Micro F1 và exact match",
            "micro-F1=2ΣTP/(2ΣTP+ΣFP+ΣFN); exact=mean(whole set equal)",
            "EXAMPLE gold={food,service}, pred={food}: TP1 FP0 FN1",
            "micro-F1=2/3; exact=0",
            "Ví dụ một mẫu multi-label",
            "src/foody/aspect.py::scores",
            "THEORY/EXAMPLE",
            "precision_recall_fscore_support; accuracy_score",
        ),
        (
            "F15",
            "Stride",
            "S = C − O",
            "256−32",
            224,
            "Bước dịch cửa sổ minh họa",
            "scripts/task2_rag_accounting.py::policy_measure",
            "THEORY/EXAMPLE",
            "policy_measure",
        ),
        (
            "F16",
            "Số chunk",
            "N=max(1,ceil((T−C)/(C−O))+1)",
            "max(1,ceil((900−256)/224)+1)",
            4,
            "Ví dụ minh họa, không rebuild index",
            "scripts/task2_rag_accounting.py",
            "THEORY/EXAMPLE",
            "policy_measure",
        ),
        (
            "F17",
            "Corpus token average",
            "T_total=Σ_i T_i; T_mean=T_total/N",
            "MiniLM 3750416/32457; Qwen4105360/32457",
            f"{3750416 / 32457:.9f}; {4105360 / 32457:.9f}",
            "Hai tokenizer, không cộng totals",
            "reports/task2/rag_token_statistics.json",
            "DERIVED",
            "scripts/task2_rag_accounting.py::summary",
        ),
        (
            "F18",
            "Raw vector payload",
            "B=N×d×bytes_per_scalar; MB=B/10⁶; MiB=B/2²⁰",
            "32457×384×4",
            f"{32457 * 384 * 4} bytes; {32457 * 384 * 4 / 1e6:.6f} MB; {32457 * 384 * 4 / 2**20:.6f} MiB",
            "Chỉ payload float32, không phải total disk/RSS",
            "src/rag/embeddings.py; Chroma manifest",
            "DERIVED",
            "LocalEmbeddings._embed(dtype=float32)",
        ),
        (
            "F19",
            "Binary Hit at k",
            "Hit@k = mean_q I(top-k intersects relevant)",
            "EXAMPLE [1,0,1]: 2/3",
            2 / 3,
            "Không dùng formula này để gọi giá trị recall cũ là Hit",
            "src/rag/evaluation.py đối chiếu semantics",
            "THEORY/EXAMPLE",
            "Chưa có binary Hit function trong accepted evaluation",
        ),
        (
            "F20",
            "Known-positive recall at k",
            "KPRecall@k = mean_q |top-k∩KP_q|/|KP_q|",
            "EXAMPLE hai positives, một vào top5: 1/2",
            0.5,
            "Code project dùng đây cho cột known_hit",
            "src/rag/evaluation.py::known_positive_scores",
            "THEORY/EXAMPLE",
            "known_positive_scores",
        ),
        (
            "F21",
            "Mean và sample standard deviation",
            "mean=Σx/n; s=sqrt(Σ(x−mean)²/(n−1))",
            "Ba test macro-F1=0.6828540656101453",
            "mean=0.6828540656101453; sample SD=0",
            "Không đo split uncertainty",
            "reports/task2/baseline_three_seed.csv",
            "DERIVED",
            "scripts/task2_finalize_evidence.py; statistics.stdev trong docs",
        ),
        (
            "F22",
            "Improvement signals",
            "Δ = metric_proposed − metric_reference",
            "0.6217892057−0.4312787686; −0.6828540656; neutral0.2577777778−0.4130434783",
            "; ".join(
                f"{v:.9f}"
                for v in (
                    0.6217892056718716 - 0.4312787685745347,
                    0.6217892056718716 - 0.6828540656101453,
                    0.2577777777777778 - 0.41304347826086957,
                )
            ),
            "Chỉ positive so với rule",
            "reports/proposed_v1/qwen_test_metrics.json; baseline JSONs",
            "DERIVED",
            "documentation arithmetic",
        ),
        (
            "F23",
            "Embedding throughput và simulation",
            "throughput=N/seconds; estimated time=chunks/throughput",
            "32457/1054.6336726; 49063/30.7756151195",
            f"{32457 / 1054.633672599999:.9f} docs/s; {49063 / (32457 / 1054.633672599999):.6f} s",
            "Thời gian alternate policy là estimate",
            "reports/task2/embedding_workload.csv",
            "DERIVED",
            "scripts/task2_rag_accounting.py",
        ),
        (
            "F24",
            "RRF",
            "RRF(d)=Σ_r 1/(k+rank_r(d))",
            "EXAMPLE A:1/61+1/64; B:2/62",
            f"A={1 / 61 + 1 / 64:.9f}; B={2 / 62:.9f}",
            "B nhỉnh hơn trong ví dụ",
            "src/rag_v2/hybrid.py::rrf_fuse",
            "THEORY/EXAMPLE",
            "rrf_fuse",
        ),
        (
            "F25",
            "BM25",
            "score(D,Q)=Σ IDF(q)×f(q,D)(k1+1)/(f(q,D)+k1(1−b+b|D|/avgdl))",
            "THEORY f=1,k1=1.2,b=.75,|D|=avgdl: multiplier=2.2/2.2",
            1,
            "SQLite trả negative rank; code đảo dấu; IDF theo FTS5",
            "src/rag_v2/lexical.py; SQLite documentation",
            "THEORY/EXAMPLE",
            "SQL bm25(reviews_fts)",
        ),
        (
            "F26",
            "Mean reciprocal rank",
            "MRR=(1/Q)Σ_q 1/rank_q; missing→0",
            "EXAMPLE (1+1/4+0)/3",
            (1 + 0.25) / 3,
            "Chỉ relevant đầu tiên",
            "src/rag/evaluation.py::known_positive_scores",
            "THEORY/EXAMPLE",
            "known_positive_scores",
        ),
        (
            "F27",
            "Mean latency",
            "L_mean=Σ latency_i/n",
            "EXAMPLE [100,200,300] ms",
            200,
            "Phải thống nhất scope retrieval/generation/end-to-end",
            "src/baselines/metrics.py; src/rag_v3/service.py",
            "THEORY/EXAMPLE",
            "measure_predictions; telemetry",
        ),
        (
            "F28",
            "Percentile p95",
            "h=(n−1)×0.95; interpolate sorted x at h",
            "EXAMPLE [100,200,300]: h=1.9, 200+.9×100",
            290,
            "Linear interpolation; minh họa không là project latency",
            "src/baselines/metrics.py; numpy/pandas default",
            "THEORY/EXAMPLE",
            "np.percentile / Series.quantile",
        ),
        (
            "F29",
            "Review vượt 128 tokens",
            "rate = n_exceed / n_docs ×100",
            "11235/32457×100",
            11235 / 32457 * 100,
            "Material embedding truncation limitation",
            "reports/task2/chunking_comparison.csv",
            "DERIVED",
            "scripts/task2_rag_accounting.py::policy_measure",
        ),
        (
            "F30",
            "V1 test token usage",
            "total=input+output; mean=total/N",
            "249190+6210=255400; 255400/887",
            255400 / 887,
            "Không cộng corpus tokenizer totals; gồm protocol request",
            "reports/proposed_v1/qwen_test_metrics.json",
            "DERIVED",
            "src/proposed_v1/runner.py::usage",
        ),
    ]


def formula_appendix(t, detailed=True):
    for ident, name, formula, substitution, result, meaning, source, kind, function in formulas():
        t.add(f"### {ident} {name}")
        t.add(f"Công thức {ident}: {formula}")
        t.add(f"Input và thế số: {substitution}. Kết quả: {fmt(result)}.")
        t.add(f"Diễn giải: {meaning}. Loại: {kind}.")
        if detailed:
            t.add(f"Trace code: {function}. Nguồn: {source}.")


def parameter_cards(t, detailed):
    for i, (name, value, candidates, why, up, down, evidence, kind) in enumerate(PARAMETERS, 1):
        if detailed:
            t.add(f"### Quyết định {i} Vì sao chọn {name}")
            t.add(f"Định nghĩa và giá trị chọn: {name} = {value}. {why}.")
            t.add(f"Ứng viên và kết quả: {candidates}. Loại selection: {kind}.")
            t.add(
                f"Nếu tăng hoặc đổi theo hướng lớn hơn: {up}. Nếu giảm hoặc đổi theo hướng nhỏ hơn: {down}."
            )
            t.add(
                "Giới hạn: "
                + (
                    "Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu."
                    if kind
                    in {
                        "ENGINEERING",
                        "ENGINEERING_WITH_SIMULATION",
                        "LIBRARY_DEFAULT",
                        "ARCHITECTURE_FIXED",
                        "CONFIGURED_WITH_LIMIT",
                    }
                    else "Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát."
                )
            )
            t.add(f"Nguồn: {evidence}.")
        else:
            t.table(
                name,
                ["Selected", "Evidence/selection"],
                [[value, candidates], [kind, evidence]],
                evidence,
                "CONFIGURED + recorded evidence",
            )


def evidence_map(t):
    for start in range(0, len(facts()), 8):
        chunk = facts()[start : start + 8]
        t.table(
            "Evidence Map " + str(start // 8 + 1),
            ["Claim", "Value", "Type / verified", "Evidence"],
            [[r[0], r[1], r[2] + " / " + r[5], r[3]] for r in chunk],
            "source paths trong từng dòng",
            "MIXED",
        )


def commands(t):
    t.add(
        "Các lệnh dưới đây là hướng dẫn, không được thực thi bởi script tài liệu. Demo dùng artifact local đã có; clone từ GitHub một mình không chứa weights/data/index. Không chạy train, download hoặc dvc repro toàn pipeline để chỉ mở demo."
    )
    t.add(r"""```powershell
# Trong thư mục project; môi trường mới dành cho kiểm tra source
py -3.12 -m venv .venv-ci
.\.venv-ci\Scripts\python.exe -m pip install -r requirements-ci.txt
.\.venv-ci\Scripts\python.exe -m pytest -q
.\.venv-ci\Scripts\python.exe -m ruff check .
.\.venv-ci\Scripts\python.exe -m compileall -q src app scripts
# Demo dùng .venv và artifacts hiện có
.\.venv\Scripts\python.exe -m src.cli demo-preflight
.\scripts\start_demo.cmd
# Hoặc launcher CPU
.\scripts\start_demo.cmd -CpuOnly
# Chỉ UI khi Qwen endpoint đúng model đã chạy
.\.venv\Scripts\python.exe -m streamlit run app/app.py
docker compose config --quiet
docker compose up -d
docker compose ps -a
docker compose logs --tail=200 pipeline
git status --short
git log -5 --oneline
git fetch origin
git tag --list
docker buildx imagetools inspect ghcr.io/iamndtk1230/mllops-food_data:v1.0.1
```""")
    t.add(
        "CI/release flow: review diff → commit/push lên branch phù hợp → xác minh CI tại đúng SHA → tạo một tag phiên bản mới chưa tồn tại → push tag → xem publish run và GHCR digest. v1.0.1 đã tồn tại, không tạo lại hoặc force-push tag. Full demo dependency provisioning có nhiều requirements và local runtime artifacts; hướng dẫn ưu tiên .venv đã nghiệm thu thay vì hứa một pip install tải đủ dữ liệu riêng."
    )


def references(t):
    t.add("## Tài liệu ngoài repository")
    t.add(
        "External literature/documentation giải thích phương pháp hoặc kiến trúc model; mọi điểm số nhóm trong tài liệu đến từ saved experiment. Không có paper macro-F1 trực tiếp tương đương trên frozen 887-row test. Không gán năm công bố nếu nguồn không chứng minh."
    )
    for title, author, year, url in EXTERNAL:
        t.add(f"{title}. {author}. {year}. {url}")
    t.add(
        "CI đã xác minh: https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39739640437"
    )
    t.add(
        "Release đã xác minh: https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39742439011"
    )


def extra(t, n):
    if n == 3:
        d = j("reports/food_dataset_report.json")
        t.table(
            "Phân bố aspect research rows",
            ["Aspect", "Rows"],
            d["aspect_counts"].items(),
            "reports/food_dataset_report.json",
        )
        t.figure(
            "reports/task2/figures/dataset_class_distribution.png", "Nguồn dữ liệu và phân bố lớp"
        )
    elif n == 5:
        s = j("data/food/splits/metadata.json")
        t.table(
            "Split và số đếm",
            ["Split", "Rows", "Review IDs", "Negative", "Neutral", "Positive"],
            [
                [
                    k,
                    s["counts"][k],
                    s["unique_reviews"][k],
                    *[s["class_distributions"][k][c] for c in ("negative", "neutral", "positive")],
                ]
                for k in ("train", "validation", "test")
            ],
            "data/food/splits/metadata.json",
        )
    elif n == 6:
        t.csv(
            "reports/task2/class_distribution.csv",
            ["class", "count", "percent"],
            ["Class", "Rows", "%"],
            "Phân bố sentiment",
        )
        t.figure(
            "reports/task2/figures/class_distribution.png", "Class imbalance trên research dataset"
        )
    elif n == 7:
        t.csv(
            "reports/task2/imbalance_comparison.csv",
            [
                "strategy",
                "class",
                "effective_weight",
                "validation_precision",
                "validation_recall",
                "validation_f1",
            ],
            ["Weight mode", "Class", "Weight", "Val P", "Val R", "Val F1"],
            "Ảnh hưởng class weight",
        )
        t.figure(
            "reports/task2/figures/imbalance_effect.png", "Validation trước và sau balanced weights"
        )
    elif n == 8:
        f = j("reports/foody_intelligence/cleaning.json")
        keys = [
            "raw_rows",
            "valid_ai_rows",
            "deduplicated_ai_observations",
            "distinct_valid_review_ids",
            "restaurant_count",
            "date_range",
            "rating_range",
            "missing_ratings",
        ]
        t.table(
            "Các đơn vị đếm Foody",
            ["Trường", "Giá trị"],
            [[k, f[k]] for k in keys],
            "reports/foody_intelligence/cleaning.json",
        )
    elif n == 13:
        t.csv(
            "reports/baselines/tfidf_experiments.csv",
            ["experiment", "ngram_range", "C", "accuracy", "macro_f1"],
            ["Trial", "Ngrams", "C", "Val accuracy", "Val macro F1"],
            "Chọn cấu hình sentiment trên validation",
        )
    elif n == 16:
        t.table(
            "Confusion minh họa không phải số liệu project",
            ["Gold / Pred", "negative", "neutral", "positive"],
            [["negative", 8, 1, 1], ["neutral", 2, 5, 3], ["positive", 1, 1, 8]],
            "Ví dụ minh họa tự dựng",
            "EXAMPLE",
        )
        t.add(
            "Ví dụ: accuracy=(8+5+8)/30=0,7. Neutral TP=5, FP=2, FN=5; P=5/7, R=5/10, F1=10/17≈0,588235. Không dùng các số này trong bảng kết quả project."
        )
        m = j("reports/baselines/tfidf_test_metrics.json")["confusion_matrix"]
        t.table(
            "Confusion TF IDF thật",
            ["Gold / Pred", "negative", "neutral", "positive"],
            [[c, *r] for c, r in zip(("negative", "neutral", "positive"), m, strict=True)],
            "reports/baselines/tfidf_test_metrics.json",
        )
    elif n == 17:
        compare = []
        for name, path in [
            ("Rule", "reports/baselines/rule_based_test_metrics.json"),
            ("TF-IDF LR", "reports/baselines/tfidf_test_metrics.json"),
            ("Qwen V1", "reports/proposed_v1/qwen_test_metrics.json"),
            ("Qwen V2-A exploratory", "reports/proposed_v2/test_metrics.json"),
        ]:
            m = j(path)
            compare.append(
                [
                    name,
                    m["accuracy"],
                    m["macro_precision"],
                    m["macro_recall"],
                    m["macro_f1"],
                    m["weighted_f1"],
                ]
            )
        t.table(
            "Sentiment test metrics cùng frozen split",
            ["Model", "Accuracy", "Macro P", "Macro R", "Macro F1", "Weighted F1"],
            compare,
            "reports/baselines/*test_metrics.json; reports/proposed_v1/qwen_test_metrics.json; reports/proposed_v2/test_metrics.json",
        )
        t.figure("reports/task2/figures/baseline_comparison.png", "Baseline và proposed sentiment")
    elif n == 18:
        t.csv(
            "reports/task2/baseline_three_seed.csv",
            ["seed", "split", "accuracy", "macro_f1", "weighted_f1", "neutral_f1"],
            ["Seed", "Split", "Accuracy", "Macro F1", "Weighted F1", "Neutral F1"],
            "Ba seed trên cùng membership",
        )
        t.csv(
            "reports/task2/linearsvc_validation_selection.csv",
            ["c", "accuracy", "macro_f1", "neutral_f1"],
            ["C", "Val accuracy", "Val macro F1", "Val neutral F1"],
            "LinearSVC supplemental selection",
        )
    elif n == 19:
        t.csv(
            "reports/proposed_v1/qwen_prompt_comparison.csv",
            [
                "prompt",
                "macro_f1",
                "json_validity_rate",
                "mean_latency_ms",
                "input_tokens",
                "output_tokens",
            ],
            ["Prompt", "Val macro F1", "JSON rate", "Mean ms", "Input tokens", "Output tokens"],
            "Prompt V1 selection",
        )
    elif n == 20:
        t.csv(
            "reports/task2/failure_counts.csv",
            ["source", "category", "count", "denominator"],
            ["Model", "Nhóm lỗi", "Errors", "Denominator"],
            "Failure taxonomy và mẫu số",
        )
    elif n == 21:
        t.csv(
            "reports/proposed_v2/prompt_comparison.csv",
            ["prompt", "example_count", "macro_f1", "neutral_f1", "mean_latency_ms"],
            ["Prompt", "Train examples", "Val macro F1", "Val neutral F1", "Mean ms"],
            "V2 A calibration",
        )
        t.figure(
            "reports/task2/figures/v1_v2_sentiment_comparison.png",
            "V1 và V2 sentiment",
            "Test V2 reused và exploratory.",
        )
    elif n == 22:
        t.csv(
            "reports/aspect_classifier/validation_comparison.csv",
            ["C", "threshold", "micro_precision", "micro_recall", "micro_f1", "macro_f1"],
            ["C", "Threshold", "Micro P", "Micro R", "Micro F1", "Macro F1"],
            "Aspect validation search",
        )
    elif n == 24:
        t.csv(
            "reports/aspect_classifier/test_per_aspect.csv",
            ["aspect", "precision", "recall", "f1", "support"],
            ["Aspect", "Precision", "Recall", "F1", "Support"],
            "Aspect test per label",
        )
        t.figure(
            "reports/task2/figures/aspect_per_class_f1.png",
            "F1 và support từng aspect",
            "Không đánh giá năng lực amenities/room khi support=0.",
        )
    elif n == 30:
        t.csv(
            "reports/task2/chunking_comparison.csv",
            [
                "policy",
                "chunk_count",
                "reviews_requiring_split",
                "duplicated_tokens_from_overlap",
                "estimated_embedding_seconds",
            ],
            ["Policy", "Chunks", "Review split", "Overlap tokens", "Estimated seconds"],
            "Simulation chunk workload",
            "DERIVED simulation; one-review reference MEASURED",
        )
        token = j("reports/task2/rag_token_statistics.json")["minilm_embedding"]["total_tokens"]
        t.table(
            "Mean content tokens mỗi chunk theo simulation",
            ["Policy", "Mean chunk tokens", "Rủi ro / storage"],
            [
                [
                    r["policy"],
                    (token + int(r["duplicated_tokens_from_overlap"])) / int(r["chunk_count"]),
                    "Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo",
                ]
                for r in rows("reports/task2/chunking_comparison.csv")
            ],
            "rag_token_statistics.json + chunking_comparison.csv",
            "DERIVED",
        )
    elif n == 31:
        data = j("reports/task2/rag_token_statistics.json")
        t.table(
            "Token statistics không truncation",
            ["Tokenizer", "Total", "Mean", "Median", "p95", "Max"],
            [
                [
                    name,
                    *[
                        data[name][k]
                        for k in (
                            "total_tokens",
                            "mean_tokens_per_document",
                            "median_tokens_per_document",
                            "p95",
                            "max",
                        )
                    ],
                ]
                for name in ("minilm_embedding", "qwen2_5_3b_generation")
            ],
            "reports/task2/rag_token_statistics.json",
        )
        t.figure("reports/task2/rag_token_distribution.png", "Phân bố token trên corpus Foody")
    elif n == 34:
        t.csv(
            "reports/rag/embedding_comparison.csv",
            [
                "model",
                "dimension",
                "known_positive_recall_at_10",
                "known_positive_mrr",
                "mean_query_embedding_ms",
            ],
            ["Model", "Dim", "KP recall10", "MRR", "Query embed ms"],
            "Embedding selection pool612",
        )
    elif n in (39, 40):
        path = (
            "reports/rag_v3/retrieval_policies.csv"
            if n == 39
            else "reports/rag_v2/retrieval_candidates.csv"
        )
        available = rows(path)
        cols = list(available[0])
        chosen = [
            key
            for key in cols
            if key
            in {
                "policy",
                "method",
                "known_hit_at_5",
                "known_hit_at_10",
                "known_mrr",
                "mean_latency_ms",
                "p95_latency_ms",
            }
        ]
        t.csv(path, chosen, title="Retrieval policy measurements")
        t.add(
            "Chú thích: các cột known_hit lưu macro known-positive recall theo known_positive_scores; không phải binary Hit. Không gộp latency giữa hai run."
        )
    elif n == 41:
        t.figure(
            "reports/task2/figures/rag_ablation_final.png",
            "Observed retrieval và safety progression",
            "Nhãn Hit của hình gốc đọc như known-positive recall; không phải causal component-off ablation.",
        )
    elif n == 49:
        t.csv(
            "reports/task2/llm_comparison.csv",
            [
                "family",
                "model_size_mb",
                "valid_schema_cases",
                "schema_applicable_cases",
                "fallback_count",
                "unknown_token_usage_cases",
            ],
            ["Family", "Size MB", "Valid schema", "Applicable", "Fallback", "Usage unknown"],
            "Ba LLM trên fixed packets",
        )
        t.csv(
            "reports/task2/llm_comparison.csv",
            [
                "family",
                "input_tokens",
                "output_tokens",
                "mean_generation_latency_ms",
                "mean_answerable_end_to_end_latency_ms",
            ],
            ["Family", "Known input", "Known output", "Active gen ms", "Answerable wall ms"],
            "Token và latency theo scope",
        )
        t.figure(
            "reports/task2/figures/three_llm_comparison.png",
            "Three family generator smoke",
            "Khác parameter scale và resource contention; không general ranking.",
        )
    elif n == 51:
        t.csv(
            "reports/task2/FEASIBILITY.csv",
            ["component", "model_size_mb", "mean_latency_ms", "p95_latency_ms", "peak_ram_bytes"],
            ["Component / run", "Model MB", "Mean ms", "p95 ms", "Peak RSS bytes"],
            "Feasibility theo từng task",
        )
        t.figure(
            "reports/task2/figures/latency_model_size.png",
            "Latency và kích thước artifact",
            "Các task/run khác nhau; DeepSeek dùng answerable wall khi active generation không có.",
        )
    elif n == 57:
        t.table(
            "Service boundary thực tế",
            ["Service", "Role", "Port / state", "Scope"],
            [
                ["pipeline", "CLI one-shot", "exit0", "--help, không ingestion"],
                ["qwen", "llama-server 3B", "8193 healthy", "CPU accepted; GPU chưa verified"],
                ["rag-backend", "FastAPI legacy", "8000 Up HTTP200", "Không phải V3 Analyst API"],
                ["streamlit", "UI + V3 modules", "8501 Up HTTP200", "Direct V3→Qwen"],
                [
                    "prefect-server/scheduler",
                    "orchestration profile",
                    "optional 4200",
                    "Không bật mặc định",
                ],
            ],
            "docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md",
            "CONFIGURED + MEASURED acceptance",
        )
    elif n == 62:
        t.add(
            '```yaml\nservices:\n  streamlit:\n    build:\n      context: .\n      dockerfile: Dockerfile.rag\n    ports: ["8501:8501"]\n```'
        )
        t.add(
            "Trích rút gọn từ docker-compose.yml: services chứa service streamlit; build.context là build context hiện tại; dockerfile chỉ image recipe; 8501 bên trái là host và bên phải là container. Các mounts/environment khác vẫn tồn tại trong file gốc."
        )
    elif n == 70:
        t.add(
            "```text\n.github/workflows/  CI và GHCR release\napp/                Streamlit và API\nconfig/             Demo selection\ndocs/experiments/   Historical research notes\nprompts/            Frozen sentiment và RAG prompts\nreports/task2/      Review 2 evidence\nreports/final/      Accepted demo summaries\nscripts/            Research, verification, launcher\nsrc/                Research và runtime modules\ntests/              Unit/synthetic/acceptance checks\ndata/ models/ state/  Local artifacts ngoài Git\n```"
        )
        for start in range(0, len(WALKTHROUGHS), 8):
            t.table(
                "Main file map",
                ["File / main symbol", "Input → output", "Caller / phase"],
                [
                    [f"{r[0]}::{r[1]}", f"{r[2]} → {r[3]}", f"{r[4]}; {r[7]}"]
                    for r in WALKTHROUGHS[start : start + 8]
                ],
                "source code + AST inventory",
                "SOURCE AUDIT",
            )
    elif n == 71:
        inv = {r["file"]: r for r in jqa("inventory.json")}
        for file, symbol, inp, out, caller, logic, failure, phase in WALKTHROUGHS:
            found = next((s for s in inv[file]["symbols"] if s["name"] == symbol), None)
            if not found:
                raise ValueError(f"Unknown symbol {file}:{symbol}")
            t.add(f"### {symbol}")
            t.add(
                f"Nguồn: {file}:{found['line']}. Vai trò: {phase}. Input: {inp}. Output: {out}. Caller: {caller}."
            )
            t.add(f"Pseudo-code và logic: {logic}. Failure cần hiểu: {failure}.")
            calls = [
                c
                for c in found["calls"]
                if any(
                    s in c
                    for s in (
                        "predict",
                        "fit",
                        "score",
                        "packet",
                        "record",
                        "search",
                        "validate",
                        "load",
                        "generate",
                        "normalize",
                        "group",
                        "split",
                    )
                )
            ]
            t.add(
                "Callee được source xác nhận: "
                + (
                    ", ".join(calls[:8])
                    or ", ".join(found["calls"][:5])
                    or "Không có call trực tiếp trong node"
                )
                + "."
            )
    elif n == 79:
        t.figure(
            "reports/task2/figures/final_architecture.png",
            "Kiến trúc logic research và demo",
            "Deployment hops cần đọc chương Docker; UI không gọi V3 qua FastAPI.",
        )
    elif n == 82:
        for start in range(0, len(PARAMETERS), 8):
            t.table(
                "Parameter selection summary",
                ["Parameter", "Selected", "Selection type", "Evidence"],
                [[p[0], p[1], p[7], p[6]] for p in PARAMETERS[start : start + 8]],
                "registry đối chiếu code/config/candidate CSV",
                "CONFIGURED + MEASURED",
            )
    elif n == 83:
        parameter_cards(t, True)
    elif n == 84:
        qa(t)
    elif n == 85:
        cheatsheet(t)


def jqa(name):
    return json.loads((QA / name).read_text(encoding="utf-8"))


def qa(t, limit=None):
    for idx, (chapter, question, risk, formula) in enumerate(QUESTIONS[:limit], 1):
        body = SECTIONS[chapter][1]
        paragraphs = body.split("\n\n")
        source = body.rsplit("Nguồn:", 1)[-1].strip()
        short = paragraphs[0].split(". ")[0] + "."
        deep = paragraphs[1].split("\nNguồn:")[0] if len(paragraphs) > 1 else paragraphs[0]
        t.add(f"### Câu hỏi {idx} {question}")
        t.add(f"Trả lời ngắn: {short}")
        t.add(f"Giải thích sâu: {deep}")
        t.add(
            f"Công thức: {formula or 'Không áp dụng phép tính riêng; xem logic source'}. Điểm dễ nhầm: {risk}"
        )
        t.add(f"Evidence và file/code để mở: {source}")


def cheatsheet(t):
    for num, title, body in [
        (
            1,
            "Số liệu",
            "Research 5869 rows; 1530 review IDs; 5316 texts. Split4140/842/887; class positive3714 negative1861 neutral294. Foody33946 raw,33938 valid,31694 observations,32457 valid distinct reviews,2110 restaurants. RAG32457 document/vector/BM25. Không nhầm row với group; xem reports/food_dataset_report.json và reports/foody_intelligence/cleaning.json.",
        ),
        (
            2,
            "Models và metrics",
            "TF-IDF LR text-only: accuracy0.809470 macro-F1 0.682854 neutral-F1 0.413043. Rule macro0.431279; QwenV1 macro0.621789; V2-A macro0.614487 exploratory. Aspect micro0.832277 macro0.633628 trên797 grouped texts. MiniLM384D CPU ONNX; Qwen3B Q4_K_M cho RAG. Nguồn: baseline/V1/V2/aspect metrics, config/demo.yaml.",
        ),
        (
            3,
            "RAG và thuật ngữ",
            "Complaint+aspect → filtered BM25/rerank; general→RRF; causal→guard. Top-k5; candidate20/nhánh; RRF60; packet≤3 reviews; 350 ký tự/evidence; output cap128; attempts2. Schema→citation→clause validation→extractive/insufficient. Historical Hit columns = KP recall. Nguồn: src/rag_v2/hybrid.py; src/rag_v3/.",
        ),
        (
            4,
            "Vận hành",
            "Local .\\scripts\\start_demo.cmd chạy preflight, Qwen3B8194 và UI8501; -CpuOnly fallback. Compose Qwen8193, API8000, UI8501; pipeline help exit0. models/reports RO; data/state RW. CI39739640437 và release39742439011 success, tagv1.0.1, commit4229a8b. Không chạy train/index để demo. Nguồn: docker-compose.yml; scripts/start_demo.ps1; public CI/CD audit.",
        ),
        (
            5,
            "Giới hạn và bảo vệ",
            "24/24 checklist là hoàn tất evidence, không production certification. Sáu RAG queries, incomplete relevance; no Foody gold; heuristic issues/support; zero-support amenities/room; embedding truncation; GPU Docker NOT VERIFIED; no LLM pretraining; CD chỉ publish. N/A phải giữ N/A. Source hiện tại thắng old prose; xem DOCUMENTATION_AUDIT.md để đối chiếu mâu thuẫn.",
        ),
    ]:
        t.add("<!-- PAGEBREAK -->")
        t.add(f"### Trang tra cứu {num} {title}")
        t.add(body)
        if num == 1:
            extra(t, 5)
            extra(t, 8)
        elif num == 2:
            t.csv(
                "reports/task2/classical_model_comparison.csv",
                ["model", "accuracy", "macro_f1", "weighted_f1"],
                ["Model", "Accuracy", "Macro F1", "Weighted F1"],
                "Research results",
            )
        elif num == 3:
            t.add(
                "Trước khi trả lời: đúng restaurant? đúng date? đúng aspect/polarity? đủ evidence? claim có frequency/causality không? refs có map đúng? fallback đã hiển thị chưa? Đây là checklist giải thích logic hiện có, không thêm guard mới."
            )
        elif num == 4:
            t.add(
                "```powershell\n.\\.venv\\Scripts\\python.exe -m src.cli demo-preflight\n.\\scripts\\start_demo.cmd\ndocker compose config --quiet\ndocker compose ps -a\n``` "
            )


def common_open(t, title, subtitle, academic=False):
    t.add(f"# {title}")
    t.add(subtitle)
    t.add(
        f"End-to-End Food Review Intelligence & LLMOps Platform\n\nNgày lập tài liệu {DATE}. Source snapshot 4229a8b3998392c97f4b7a8c9e3795830285dbce."
    )
    if academic:
        t.add(
            "Nhóm thực hiện: [Điền tên nhóm và thành viên]. Giảng viên: [Điền họ tên]. Học phần/lớp: [Điền thông tin]."
        )
    t.add(
        "Tài liệu phân biệt MEASURED (đo đã lưu), DERIVED (tính lại), CONFIGURED (tham số code/config), EXTERNAL (nguồn ngoài). THEORY và EXAMPLE không phải kết quả project. Các đường dẫn source tính từ thư mục gốc repository."
    )
    t.add("<!-- TOC -->")


def build_master():
    t = Text()
    common_open(
        t,
        "Hướng dẫn toàn bộ Food Review Intelligence bằng tiếng Việt",
        "Tài liệu học và bảo vệ thiết kế kỹ thuật",
    )
    t.add(
        "Mục tiêu đọc: hiểu bài toán, lần theo dữ liệu và code, tính lại chỉ số và giải thích quyết định. Đọc chương1–25 cho dữ liệu/ML,26–52 cho RAG/LLM,53–69 cho vận hành và70–85 để tra cứu/bảo vệ. Kết quả nổi bật là classifier TF-IDF được chọn cho sentiment, Qwen3B phục vụ RAG có evidence gates, và24/24 checklist đã có evidence với các giới hạn khoa học giữ nguyên."
    )
    for n, (title, body) in SECTIONS.items():
        t.add(f"## Chương {n} {title}")
        t.add(body.replace("span_starts/policy_measure", "policy_measure"))
        extra(t, n)
    t.add("<!-- PAGEBREAK -->")
    t.add("## Phụ lục A Công thức và phép tính")
    formula_appendix(t)
    t.add("## Phụ lục B Code to math traceability")
    for start in range(0, len(formulas()), 8):
        t.table(
            "Trace công thức đến implementation",
            ["Concept / formula", "Function", "Input → output evidence"],
            [[f"{f[0]} {f[1]}", f[8], f[6]] for f in formulas()[start : start + 8]],
            "source code cited in từng dòng",
            "SOURCE AUDIT",
        )
    t.add("## Phụ lục C Lệnh tái lập và vận hành")
    commands(t)
    t.add("## Phụ lục D Evidence và source map")
    evidence_map(t)
    t.add("## Phụ lục E Mâu thuẫn tài liệu và quyết định xử lý")
    for title, old, new, source in CONTRADICTIONS:
        t.add(f"### {title}")
        t.add(f"Phát hiện: {old}. Kết luận dùng trong tài liệu: {new}. Nguồn: {source}.")
    references(t)
    return t


def build_report():
    t = Text()
    common_open(
        t,
        "End-to-End Food Review Intelligence & LLMOps Platform",
        "Báo cáo học thuật Task 2 Review 2",
        True,
    )
    t.add("## Tóm tắt điều hành")
    t.add(
        "Nghiên cứu xây dựng hệ thống phân tích review nhà hàng tiếng Việt và phục vụ hỏi đáp có bằng chứng. VN-MSASar v3 cung cấp5869 dòng câu–aspect với split4140/842/887; Foody first-party cung cấp33946 dòng nguồn,32457 review hợp lệ riêng biệt và2110 nhà hàng cho inference/RAG. TF-IDF LR đạt test macro-F1 0,682854, cao hơn rule0,431279 và Qwen V1 0,621789, nên được giữ cho phân loại. RAG V3 dùng routing, Chroma/BM25, packet, Qwen3B và validator/fallback. Sáu ca replay cho2 supported complete,1 incomplete,3 correct insufficient và0 validator-detected unsupported accepted. Docker local và image delivery GHCR đã xác minh; không claim production deployment hoặc LLM training from scratch."
    )
    chapter_map = {
        1: [1],
        2: [3, 8],
        3: [4],
        4: [5],
        5: [6, 7],
        6: [75],
        7: [11, 17],
        8: [18],
        9: [],
        10: [20],
        11: [19],
        12: [20],
        13: [21],
        14: [39, 40, 41],
        15: [29, 30],
        16: [32, 34, 35],
        17: [42, 43, 44],
        18: [45, 46, 47],
        19: [],
        20: [49],
        21: [50, 51],
        22: [79],
        23: [57, 60, 61],
        24: [64, 66, 67, 68],
        25: [74],
        26: [76],
        27: [81],
        28: [],
        29: [],
        30: [],
    }
    # Academic report uses one concise central paragraph per topic, with tables carrying detail.
    extra_map = {
        2: [8],
        4: [5],
        5: [7],
        7: [13, 17],
        8: [18],
        11: [19],
        12: [20],
        13: [21],
        14: [39],
        15: [30, 31],
        16: [34],
        18: [],
        19: [41],
        20: [49],
        21: [51],
        22: [79],
        23: [57],
    }
    for n, title in enumerate(REPORT_TITLES, 1):
        t.add(f"## {n} {title}")
        for c in chapter_map[n]:
            body = SECTIONS[c][1]
            paras = body.split("\n\n")
            selected = paras[0]
            if c in {5, 7, 8, 19, 20, 21, 29, 34, 41, 49, 50, 51, 54, 57, 68, 74, 76, 81}:
                selected += "\n\n" + paras[1]
            t.add(selected)
            t.add("Nguồn: " + body.rsplit("Nguồn:", 1)[-1].strip())
        if n == 1:
            t.add(
                "In scope: benchmark text-only, classifier aspect, Foody inference/marts, local RAG V3, UI, telemetry, Docker/CI/CD evidence. Out of scope: full LLM training from scratch, production remote rollout, Foody gold accuracy và thay đổi artifact đã đóng băng."
            )
        elif n == 2:
            t.csv(
                "reports/task2/dataset_sources.csv",
                list(rows("reports/task2/dataset_sources.csv")[0])[:4],
                title="Dataset source registry",
            )
        elif n == 3:
            t.add(
                "VN-MSASar labels do dataset cung cấp; không có annotation nhiều người mới hoặc Kappa của nhóm nên Kappa=N/A. Foody hiện hành không có Classification; rating giữ vai trò metadata. NFC/whitespace giữ dấu, case và nguồn gốc. Loại khỏi AI không đồng nghĩa xóa source row. Các export review.csv cũ là supplementary historical evidence."
            )
        elif n == 4:
            t.add("Split SHA256: " + j("data/food/splits/metadata.json")["split_file_sha256"])
        elif n == 9:
            t.add(
                "Không có baseline paper tái lập với cùng filtered dataset, label normalization, input và887-row test. Rule lexicon do nhóm xây; LR/SVC là implementation sklearn. Dataset/model/method documentation không cung cấp một paper macro-F1 tương đương. Vì vậy numerical paper–group gap=N/A và NOT DIRECTLY COMPARABLE. Hoàn thành checklist mục này có nghĩa hoàn thành source audit, không chứng minh replication thành công."
            )
            t.csv(
                "reports/task2/classical_model_comparison.csv",
                ["model", "accuracy", "macro_f1"],
                ["Local model", "Group accuracy", "Group macro F1"],
                "Kết quả nhóm không phải điểm paper",
            )
        elif n == 10:
            t.add(
                "Research gap xác minh: neutral ít và text-only không biểu diễn aspect ambiguity. Domain shift/hyperparameter/pretraining là giả thuyết chưa được isolate. Hướng cải thiện được kiểm bằng prompt calibration và aspect input; RAG V3 giải quyết grounding demo, không nâng sentiment macro-F1 của classifier."
            )
        elif n == 13:
            t.add(
                "V2-A và V2-B phải tách tên: text-only calibration so với text+aspect research. Cả hai tái sử dụng test đã xem, không là xác nhận held-out độc lập. Không thay sentiment production artifact."
            )
        elif n == 17:
            t.add(
                "Tên cột known_hit_at_5/10 được giữ để trace, nhưng ý nghĩa công thức là macro known-positive recall. Binary Hit@k và full Recall@k được giải thích riêng ở phụ lục; không đổi experiment results. MRR V3=0,166667 là mean reciprocal rank trên sáu query."
            )
        elif n == 18:
            t.table(
                "Accepted Qwen3B six-case outcomes",
                ["Outcome", "Count", "Interpretation"],
                [
                    ["supported complete", 2, "1 synthesis + 1 fallback"],
                    ["supported incomplete", 1, "fallback không chứng minh phổ biến nhất"],
                    ["unsupported accepted", 0, "validator-detected only"],
                    ["correct insufficient", 3, "không generation khi evidence thiếu"],
                    ["fallback", 2, "subset của supported answers"],
                ],
                "reports/rag_v3/generation_metrics.json",
            )
        elif n == 19:
            t.add(
                "Đây là ablation theo observed progression từ saved artifacts. Không có component-off controls để ước lượng causal effect của packet, validator hay fallback. Evidence packet chấp nhận3 và từ chối3; clause validator ghi5 rejected attempts của Qwen3B; final system giữ useful evidence bằng2 fallbacks. Attempt count không phải số final answers độc lập. Blank/N/A không được thay bằng0."
            )
        elif n == 24:
            t.add(
                "Public API và GHCR read-only audit22/10/2026 xác nhận post-fix v1.0.1, mới hơn report CICD_EVIDENCE trong repo. CI/release tại4229a8b không bao phủ các tài liệu đang tạo. Image digest đầy đủ nằm ở Evidence Map. Các tag/alias theo workflow, không giả định deployment."
            )
        elif n == 25:
            t.add(
                "Dataset revision6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4; split hash860387be19c64220f91cc2b5e764aa3c99aa18daba9c776fde38e05da30a5ff9; seed42; model/prompt hashes trong provenance/selection; DVC lock và requirements pins trong repo. Last recorded tests288 passed1 warning, Ruff/compileall PASS. Tài liệu tái tính từ saved outputs và không retrain/retest model."
            )
        elif n == 28:
            t.add(
                "Kết quả ủng hộ kiến trúc chia vai trò: TF-IDF LR cho classification, model aspect độc lập cho chủ đề, Qwen cho diễn đạt evidence và deterministic gates cho khả năng kiểm chứng. V1/V2 không được quảng bá là vượt baseline mạnh; RAG V3 được chấp nhận trong tập ca local giới hạn. Đóng góp Task2 là chuỗi experiment có failure analysis, accounting tài nguyên, source traceability và runtime/image-delivery evidence. Bước tiếp theo nên ưu tiên relevance set và human support evaluation độc lập trước khi đổi kiến trúc."
            )
        elif n == 29:
            original = (ROOT / "reports/task2/TASK2_SELF_ASSESSMENT.md").read_text(encoding="utf-8")
            data = []
            for line in original.splitlines():
                if re.match(r"\| \d+\.", line):
                    parts = [x.strip().strip("`") for x in line.strip("|").split("|")]
                    data.append(parts[:3])
            assert len(data) == 24 and all(r[1] == "DONE" for r in data)
            t.table(
                "Task2 teacher checklist",
                ["Item", "Status", "Evidence / limit"],
                data,
                "reports/task2/TASK2_SELF_ASSESSMENT.md",
                "AUDITED STATUS",
            )
            t.add(
                "24/24 DONE theo tiêu chí evidence của checklist. Caveats giữ nguyên: không full LLM training from scratch, không production remote deployment, GPU Docker chưa xác minh, benchmark sáu ca và observational ablation không chứng minh general superiority."
            )
        elif n == 30:
            t.add("### A Lệnh vận hành")
            commands(t)
            t.add("### B Repo map")
            t.table(
                "Module groups",
                ["Group", "Role"],
                [
                    ["src/food + baselines + proposed*", "Research frozen experiments"],
                    ["src/foody", "Offline inference và marts"],
                    ["src/rag + rag_v2 + rag_v3", "Shared retrieval và active V3 safety"],
                    ["app + config + prompts", "UI/API và serving selection"],
                    ["scripts + tests", "Research/verify/launch và tests"],
                    [".github + Dockerfiles", "CI và image delivery"],
                ],
                "source inventory",
                "SOURCE AUDIT",
            )
            t.add("### C Config và artifact identities")
            t.add(
                "Active sentiment=models/tfidf_logreg.joblib; aspect=models/aspect_tfidf.joblib; Qwen3B revisioncc1e68eea5f05f88f41a6de1fc73110178f23715; embedding revisionfaf4aa4225822f3bc6376869cb1164e8e3feedd0; prompt rag_v3:81e19ef10f78. Nguồn: config/demo.yaml; qwen_v3_3b.yaml; reports/rag/embedding_selection.json."
            )
            t.add("### D Công thức")
            formula_appendix(t, False)
            t.add("### E Parameter selection")
            t.table(
                "Validation selected và fixed choices",
                ["Parameter", "Selected", "Evidence/limit"],
                [
                    [p[0], p[1], p[2]]
                    for p in PARAMETERS
                    if p[7] not in {"ENGINEERING", "LIBRARY_DEFAULT", "CONFIGURED_WITH_LIMIT"}
                ],
                "source config/candidate CSV",
                "CONFIGURED + MEASURED",
            )
            t.add(
                "Các giá trị cố định như max_features, min_df, RRF60, top-k5, packet3, context2048, temperature0, quantization và ports không có controlled search riêng. Full32 decision cards và ảnh hưởng tăng/giảm ở Master Guide/notebook."
            )
            t.add("### F Evidence index")
            evidence_map(t)
            t.add("### G Câu hỏi bảo vệ")
            qa(t, 12)
        for c in extra_map.get(n, []):
            extra(t, c)
    references(t)
    return t


def notebook():
    t = Text()
    t.add("# Notebook tính toán và bảo vệ tham số Task 2")
    t.add(
        "Đọc saved evidence, không suy luận lại hoặc huấn luyện model. Mọi phép tính chỉ tạo documentation. MEASURED giữ metric gốc; DERIVED tính lại; THEORY/EXAMPLE luôn ghi rõ. Phương pháp tính nằm trong scripts/documentation/generate_project_docs.py::formulas."
    )
    formula_appendix(t)
    t.add("## Tính lại classification từ confusion matrix")
    for name, path in [
        ("Rule", "reports/baselines/rule_based_test_metrics.json"),
        ("TF-IDF", "reports/baselines/tfidf_test_metrics.json"),
    ]:
        obj = j(path)
        mat = obj["confusion_matrix"]
        per = []
        for k, label in enumerate(("negative", "neutral", "positive")):
            tp = mat[k][k]
            fp = sum(row[k] for row in mat) - tp
            fn = sum(mat[k]) - tp
            p = tp / (tp + fp) if tp + fp else 0
            r = tp / (tp + fn) if tp + fn else 0
            f = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
            per.append([label, tp, fp, fn, p, r, f])
        assert abs(statistics.mean(row[-1] for row in per) - obj["macro_f1"]) < 1e-12
        t.table(
            name + " confusion-derived",
            ["Class", "TP", "FP", "FN", "P", "R", "F1"],
            per,
            path,
            "DERIVED",
        )
    t.add("## Token histogram consistency")
    hist = rows("reports/task2/rag_token_distribution.csv")
    tok = j("reports/task2/rag_token_statistics.json")
    for name in ("minilm_embedding", "qwen2_5_3b_generation"):
        own = [r for r in hist if r["tokenizer"] == name]
        n = sum(int(r["review_count"]) for r in own)
        total = sum(int(r["review_count"]) * int(r["tokens_per_review"]) for r in own)
        assert n == tok[name]["document_count"] and total == tok[name]["total_tokens"]
        t.add(
            f"{name}: Σ review_count={n}; Σ tokens_per_review×review_count={total}; average={total / n:.9f}. Nguồn: reports/task2/rag_token_distribution.csv. DERIVED và đối chiếu JSON: PASS."
        )
    t.add("## Parameter defense notebook")
    parameter_cards(t, True)
    return t


def audit_document():
    t = Text()
    t.add("# Documentation audit")
    inventory = jqa("inventory.json")
    t.add(
        f"Audit read-only {DATE}; source HEAD4229a8b. Đã đọc {len(inventory)} file text/source, phân tích AST của Python và checksum701 file protected trước authoring. Inventory là phân tích static; caller động có thể không suy ra hết. Các file dataset/model binary được checksum/đối chiếu manifest, không coi là văn bản để đọc. Không có claim đã kiểm toán mọi byte dependency bên thứ ba."
    )
    t.table(
        "Claim and metric audit",
        [
            "Claim / Metric",
            "Documented value",
            "Type",
            "Source",
            "Recalculated?",
            "Verified?",
            "Notes",
        ],
        facts(),
        "evidence cited per row",
        "MIXED",
    )
    t.add("### Resolved Documentation Contradictions — Mâu thuẫn và cách xử lý")
    t.table(
        "Contradiction register",
        ["Claim", "Stale/ambiguous", "Resolution", "Evidence"],
        CONTRADICTIONS,
        "code precedes old prose",
        "SOURCE AUDIT",
    )
    t.add("## Unsupported information")
    t.add(
        "Không có paper macro-F1 cùng filtered split; Foody gold accuracy; issue supervised accuracy; Kappa manual labeling mới; full-corpus relevance recall; exhaustive embedding search; controlled safety component-off effects; peak V1 inference resources bị mất; general population hallucination rate; GPU Docker assignment; remote production rollout; log đủ xác minh scenario push-rejected/rebase. Các mục này được ghi N/A, limitation hoặc EXAMPLE thay vì sáng tác."
    )
    t.add("## Parameter choices without controlled experiments")
    t.table(
        "Fixed choices",
        ["Parameter", "Value", "Evidence / uncertainty"],
        [
            [p[0], p[1], p[2]]
            for p in PARAMETERS
            if p[7]
            in {
                "ENGINEERING",
                "ENGINEERING_WITH_SIMULATION",
                "LIBRARY_DEFAULT",
                "ARCHITECTURE_FIXED",
                "CONFIGURED_WITH_LIMIT",
            }
        ],
        "code/config registry",
        "CONFIGURED",
    )
    t.add("## Repository inventory đã đọc")
    for prefix in (
        "src/",
        "app/",
        "scripts/",
        "tests/",
        "databricks/",
        ".github/",
        "config/",
        "docs/experiments/",
    ):
        subset = [r for r in inventory if r["file"].startswith(prefix)]
        t.table(
            prefix,
            ["File", "Main symbols", "Caller modules"],
            [
                [
                    r["file"],
                    ", ".join(
                        s["name"]
                        for s in r["symbols"]
                        if s["kind"] == "ClassDef" or not s["name"].startswith("_")
                    )[:550],
                    ", ".join(r["called_by_modules"])[:300],
                ]
                for r in subset
            ],
            "AST inventory static",
            "SOURCE AUDIT",
        )
    t.add("## Report evidence coverage")
    t.add(
        "\n".join(
            "- " + r["file"] + " — SHA256 " + r["sha256"]
            for r in inventory
            if r["file"].startswith(("reports/task2/", "reports/final/"))
        )
    )
    t.add("## Quality verification")
    t.add(
        "QA định lượng, render và kiểm tra bảo toàn file được cập nhật sau generation. Xem phần kết quả kiểm tra cuối file. Không có production source, config, data, model, index hay experiment report được phép ghi bởi generator."
    )
    return t


def clean_inline(text):
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text.replace("**", "").replace("`", "")


def set_font(run, size=None, bold=None):
    run.font.name = "Times New Roman"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)


def field(paragraph, instruction):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    text = OxmlElement("w:instrText")
    text.set(qn("xml:space"), "preserve")
    text.text = instruction
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, text, sep, end])


def word_table(doc, lines):
    parsed = [
        [clean_inline(v.strip()) for v in line.strip().strip("|").split("|")] for line in lines
    ]
    data = [r for r in parsed if not all(re.fullmatch(r"[:\- ]+", v or "-") for v in r)]
    cols = len(data[0])
    table = doc.add_table(rows=0, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    total = 16.5
    lengths = [sum(min(len(row[i]), 100) for row in data) / max(1, len(data)) for i in range(cols)]
    weights = [max(9, min(48, n)) ** 0.65 for n in lengths]
    widths = [total * w / sum(weights) for w in weights]
    if cols == 2:
        widths = [5.2, 11.3]
    for col, w in zip(table.columns, widths, strict=True):
        col.width = Cm(w)
    borders = OxmlElement("w:tblBorders")
    for name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + name)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "D9D9D9")
        borders.append(el)
    table._tbl.tblPr.append(borders)
    for idx, values in enumerate(data):
        row = table.add_row()
        if idx == 0:
            h = OxmlElement("w:tblHeader")
            row._tr.get_or_add_trPr().append(h)
        cant = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant)
        for i, (cell, value) in enumerate(zip(row.cells, values, strict=True)):
            cell.width = Cm(widths[i])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr = cell._tc.get_or_add_tcPr()
            marg = OxmlElement("w:tcMar")
            for side in ("top", "left", "bottom", "right"):
                e = OxmlElement("w:" + side)
                e.set(qn("w:w"), "70")
                e.set(qn("w:type"), "dxa")
                marg.append(e)
            tcpr.append(marg)
            fill = "DCE6F1" if idx == 0 else ("F5F7FA" if idx % 2 == 0 else "FFFFFF")
            sh = OxmlElement("w:shd")
            sh.set(qn("w:fill"), fill)
            tcpr.append(sh)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.line_spacing = 1.05
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            # Allow line breaks at slash boundaries in long repository paths.
            value = value.replace("/", "/\u200b").replace("_", "_\u200b")
            run = p.add_run(value)
            set_font(run, 9 if cols >= 5 else 10, idx == 0)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def docx_from_markdown(path):
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2.2)
    section.left_margin = section.right_margin = Cm(2.25)
    section.header_distance = section.footer_distance = Cm(1.1)
    for name, size, bold in (
        ("Normal", 12, False),
        ("Title", 22, True),
        ("Heading 1", 16, True),
        ("Heading 2", 14, True),
        ("Heading 3", 12, True),
        ("Caption", 10, False),
    ):
        s = doc.styles[name]
        s.font.name = "Times New Roman"
        s.font.size = Pt(size)
        s.font.bold = bold
        s.font.color.rgb = RGBColor(0, 0, 0)
        s._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.line_spacing = 1.15
        if name.startswith("Heading"):
            s.paragraph_format.keep_with_next = True
            s.paragraph_format.space_before = Pt(12)
    doc.styles["Normal"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.styles["Caption"].font.italic = True
    hp = section.header.paragraphs[0]
    hp.add_run("Food Review Intelligence và LLMOps")
    set_font(hp.runs[0], 10)
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field(fp, " PAGE ")
    doc.core_properties.title = path.stem
    doc.core_properties.subject = "Vietnamese documentation grounded in frozen project evidence"
    doc.core_properties.author = "Food Review Intelligence project"
    settings = doc.settings.element
    up = OxmlElement("w:updateFields")
    up.set(qn("w:val"), "true")
    settings.append(up)
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    code = False
    figures = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip():
            continue
        if line.startswith("```"):
            code = not code
            continue
        if code:
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(line)
            set_font(run, 10)
            continue
        if line == "<!-- PAGEBREAK -->":
            doc.add_page_break()
            continue
        if line == "<!-- TOC -->":
            doc.add_page_break()
            doc.add_heading("Mục lục", level=1)
            field(doc.add_paragraph(), ' TOC \\o "1-2" \\h \\z \\u ')
            p = doc.add_paragraph("Right-click TOC → Update Field → Update entire table.")
            p.style = "Caption"
            doc.add_page_break()
            continue
        if line.startswith("|"):
            group = [line]
            while i < len(lines) and lines[i].startswith("|"):
                group.append(lines[i])
                i += 1
            word_table(doc, group)
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if m:
            image = (path.parent / m.group(2)).resolve()
            with Image.open(image) as im:
                w, h = im.size
            width = min(16.5, 15 * w / h)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            pic = p.add_run().add_picture(str(image), width=Cm(width))
            pic._inline.docPr.set("descr", m.group(1))
            figures += 1
            continue
        m = re.match(r"(#+) (.*)", line)
        if m:
            level = len(m.group(1))
            text = clean_inline(m.group(2))
            p = doc.add_paragraph(
                text, style="Title" if level == 1 else f"Heading {min(level - 1, 3)}"
            )
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue
        if line.startswith(("Hình ", "Bảng ", "Nguồn:")):
            p = doc.add_paragraph(clean_inline(line), style="Caption")
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if line.startswith("Bảng "):
                p.paragraph_format.keep_with_next = True
            continue
        if line.startswith("Công thức F"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            math_el = OxmlElement("m:oMath")
            mr = OxmlElement("m:r")
            mt = OxmlElement("m:t")
            mt.text = line
            mr.append(mt)
            math_el.append(mr)
            p._p.append(math_el)
            continue
        if line.startswith("- "):
            p = doc.add_paragraph(clean_inline(line[2:]), style="List Bullet")
        else:
            p = doc.add_paragraph(clean_inline(line))
        for run in p.runs:
            set_font(run)
    target = path.with_suffix(".docx")
    doc.save(target)
    check = Document(target)
    assert len(check.inline_shapes) == figures
    return {
        "path": str(target),
        "paragraphs": len(check.paragraphs),
        "tables": len(check.tables),
        "figures": figures,
        "top_level_sections": sum(1 for p in check.paragraphs if p.style.name == "Heading 1"),
        "formula_count": len(check.element.xpath("//m:oMath")),
        "qa_questions": sum(1 for p in check.paragraphs if p.text.startswith("Câu hỏi ")),
    }


def main():
    if not (QA / "inventory.json").exists():
        raise RuntimeError("Run audit_repository.py first")
    OUT.mkdir(exist_ok=True)
    products = {
        "PROJECT_MASTER_GUIDE_VI": build_master(),
        "TASK2_REVIEW2_REPORT_VI": build_report(),
        "TASK2_CALCULATION_NOTEBOOK_VI": notebook(),
        "DOCUMENTATION_AUDIT": audit_document(),
    }
    results = []
    for name, body in products.items():
        path = OUT / (name + ".md")
        path.write_text(body.value(), encoding="utf-8")
        if name in {"PROJECT_MASTER_GUIDE_VI", "TASK2_REVIEW2_REPORT_VI"}:
            results.append(docx_from_markdown(path))
    (QA / "document_stats.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
