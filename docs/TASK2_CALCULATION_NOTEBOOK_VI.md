# Notebook tính toán và bảo vệ tham số Task 2

Đọc saved evidence, không suy luận lại hoặc huấn luyện model. Mọi phép tính chỉ tạo documentation. MEASURED giữ metric gốc; DERIVED tính lại; THEORY/EXAMPLE luôn ghi rõ. Phương pháp tính nằm trong scripts/documentation/generate_project_docs.py::formulas.

### F01 Imbalance ratio

Công thức F01: IR = max(n_c) / min(n_c)

Input và thế số: 3714 / 294. Kết quả: 12.632653.

Diễn giải: Lớp đông gấp 12,63 lần lớp ít. Loại: DERIVED.

Trace code: Không có function model; phép tính documentation. Nguồn: reports/task2/class_distribution.csv.

### F02 Balanced class weights

Công thức F02: w_c = N / (K × n_c)

Input và thế số: 4140/(3×1307); 4140/(3×208); 4140/(3×2625). Kết quả: 1.055853099; 6.634615385; 0.525714286.

Diễn giải: Train-only; không đổi số mẫu. Loại: DERIVED.

Trace code: src/baselines/tfidf_logreg.py::build_pipeline. Nguồn: reports/task2/imbalance_comparison.csv.

### F03 Term frequency

Công thức F03: TF_intro = count / length; TF_project = 1 + ln(count) nếu count>0

Input và thế số: EXAMPLE count=3,length=10: 3/10; 1+ln(3). Kết quả: 0.3; 2.098612289.

Diễn giải: Ví dụ minh họa, không phải số liệu project. Loại: THEORY/EXAMPLE.

Trace code: TfidfVectorizer(sublinear_tf=True). Nguồn: src/baselines/tfidf_logreg.py.

### F04 Smoothed IDF

Công thức F04: IDF = ln((1+N)/(1+df)) + 1

Input và thế số: EXAMPLE N=100,df=10: ln(101/11)+1. Kết quả: 3.217225.

Diễn giải: Vocabulary/IDF học train; minh họa. Loại: THEORY/EXAMPLE.

Trace code: TfidfVectorizer(smooth_idf=True mặc định). Nguồn: src/baselines/tfidf_logreg.py; sklearn API.

### F05 TF IDF và L2

Công thức F05: u_t = TF_t × IDF_t; x = u / sqrt(Σ u_t²)

Input và thế số: EXAMPLE u=[3,4] → norm=5. Kết quả: [0.6,0.8].

Diễn giải: Minh họa chuẩn hóa vector, không phải review embedding. Loại: THEORY/EXAMPLE.

Trace code: TfidfVectorizer(norm='l2' mặc định). Nguồn: src/baselines/tfidf_logreg.py.

### F06 Logistic sigmoid

Công thức F06: z = wᵀx+b; σ(z)=1/(1+exp(−z))

Input và thế số: EXAMPLE z=0. Kết quả: 0.500000.

Diễn giải: Nhị phân OVR aspect, không công thức 3-class sentiment. Loại: THEORY/EXAMPLE.

Trace code: OneVsRestClassifier(LogisticRegression). Nguồn: src/foody/aspect.py.

### F07 Multinomial softmax

Công thức F07: p_c = exp(z_c) / Σ_j exp(z_j)

Input và thế số: EXAMPLE scores=[0,0,0]. Kết quả: [1/3,1/3,1/3].

Diễn giải: Xác suất ba lớp cộng thành1. Loại: THEORY/EXAMPLE.

Trace code: LogisticRegression(solver='lbfgs'). Nguồn: src/baselines/tfidf_logreg.py.

### F08 Accuracy thật từ confusion

Công thức F08: accuracy = Σ diagonal / N

Input và thế số: (228+19+471)/887. Kết quả: 0.809470.

Diễn giải: Tính lại prediction đã lưu, không test inference mới. Loại: DERIVED.

Trace code: src/baselines/metrics.py::scores → accuracy_score. Nguồn: reports/baselines/tfidf_test_metrics.json.

### F09 Neutral precision

Công thức F09: P = TP/(TP+FP)

Input và thế số: 19/(9+19+21). Kết quả: 0.387755.

Diễn giải: 49 predicted-neutral, 19 đúng. Loại: DERIVED.

Trace code: src/baselines/metrics.py::class_report. Nguồn: reports/baselines/tfidf_test_metrics.json.

### F10 Neutral recall

Công thức F10: R = TP/(TP+FN)

Input và thế số: 19/(10+19+14). Kết quả: 0.441860.

Diễn giải: Tìm được19 trong43 gold-neutral. Loại: DERIVED.

Trace code: precision_recall_fscore_support. Nguồn: reports/baselines/tfidf_test_metrics.json.

### F11 Neutral F1

Công thức F11: F1 = 2PR/(P+R) = 2TP/(2TP+FP+FN)

Input và thế số: 38/(38+30+24). Kết quả: 0.413043.

Diễn giải: Trade-off precision/recall. Loại: DERIVED.

Trace code: src/baselines/metrics.py::scores. Nguồn: reports/baselines/tfidf_test_metrics.json.

### F12 Macro F1

Công thức F12: macro-F1 = (Σ_c F1_c)/K

Input và thế số: (0.7728813559322034+0.4130434782608696+0.8626373626373627)/3. Kết quả: 0.682854.

Diễn giải: Mỗi lớp cùng trọng số. Loại: DERIVED.

Trace code: precision_recall_fscore_support(average='macro'). Nguồn: reports/baselines/tfidf_test_metrics.json.

### F13 Weighted F1

Công thức F13: weighted-F1 = Σ support_c×F1_c / N

Input và thế số: (284×F1_negative+43×F1_neutral+560×F1_positive)/887. Kết quả: 0.812104.

Diễn giải: Lớp đông ảnh hưởng lớn. Loại: DERIVED.

Trace code: precision_recall_fscore_support(average='weighted'). Nguồn: reports/baselines/tfidf_test_metrics.json.

### F14 Micro F1 và exact match

Công thức F14: micro-F1=2ΣTP/(2ΣTP+ΣFP+ΣFN); exact=mean(whole set equal)

Input và thế số: EXAMPLE gold={food,service}, pred={food}: TP1 FP0 FN1. Kết quả: micro-F1=2/3; exact=0.

Diễn giải: Ví dụ một mẫu multi-label. Loại: THEORY/EXAMPLE.

Trace code: precision_recall_fscore_support; accuracy_score. Nguồn: src/foody/aspect.py::scores.

### F15 Stride

Công thức F15: S = C − O

Input và thế số: 256−32. Kết quả: 224.

Diễn giải: Bước dịch cửa sổ minh họa. Loại: THEORY/EXAMPLE.

Trace code: policy_measure. Nguồn: scripts/task2_rag_accounting.py::policy_measure.

### F16 Số chunk

Công thức F16: N=max(1,ceil((T−C)/(C−O))+1)

Input và thế số: max(1,ceil((900−256)/224)+1). Kết quả: 4.

Diễn giải: Ví dụ minh họa, không rebuild index. Loại: THEORY/EXAMPLE.

Trace code: policy_measure. Nguồn: scripts/task2_rag_accounting.py.

### F17 Corpus token average

Công thức F17: T_total=Σ_i T_i; T_mean=T_total/N

Input và thế số: MiniLM 3750416/32457; Qwen4105360/32457. Kết quả: 115.550297316; 126.486120097.

Diễn giải: Hai tokenizer, không cộng totals. Loại: DERIVED.

Trace code: scripts/task2_rag_accounting.py::summary. Nguồn: reports/task2/rag_token_statistics.json.

### F18 Raw vector payload

Công thức F18: B=N×d×bytes_per_scalar; MB=B/10⁶; MiB=B/2²⁰

Input và thế số: 32457×384×4. Kết quả: 49853952 bytes; 49.853952 MB; 47.544434 MiB.

Diễn giải: Chỉ payload float32, không phải total disk/RSS. Loại: DERIVED.

Trace code: LocalEmbeddings._embed(dtype=float32). Nguồn: src/rag/embeddings.py; Chroma manifest.

### F19 Binary Hit at k

Công thức F19: Hit@k = mean_q I(top-k intersects relevant)

Input và thế số: EXAMPLE [1,0,1]: 2/3. Kết quả: 0.666667.

Diễn giải: Không dùng formula này để gọi giá trị recall cũ là Hit. Loại: THEORY/EXAMPLE.

Trace code: Chưa có binary Hit function trong accepted evaluation. Nguồn: src/rag/evaluation.py đối chiếu semantics.

### F20 Known-positive recall at k

Công thức F20: KPRecall@k = mean_q |top-k∩KP_q|/|KP_q|

Input và thế số: EXAMPLE hai positives, một vào top5: 1/2. Kết quả: 0.500000.

Diễn giải: Code project dùng đây cho cột known_hit. Loại: THEORY/EXAMPLE.

Trace code: known_positive_scores. Nguồn: src/rag/evaluation.py::known_positive_scores.

### F21 Mean và sample standard deviation

Công thức F21: mean=Σx/n; s=sqrt(Σ(x−mean)²/(n−1))

Input và thế số: Ba test macro-F1=0.6828540656101453. Kết quả: mean=0.6828540656101453; sample SD=0.

Diễn giải: Không đo split uncertainty. Loại: DERIVED.

Trace code: scripts/task2_finalize_evidence.py; statistics.stdev trong docs. Nguồn: reports/task2/baseline_three_seed.csv.

### F22 Improvement signals

Công thức F22: Δ = metric_proposed − metric_reference

Input và thế số: 0.6217892057−0.4312787686; −0.6828540656; neutral0.2577777778−0.4130434783. Kết quả: 0.190510437; -0.061064860; -0.155265700.

Diễn giải: Chỉ positive so với rule. Loại: DERIVED.

Trace code: documentation arithmetic. Nguồn: reports/proposed_v1/qwen_test_metrics.json; baseline JSONs.

### F23 Embedding throughput và simulation

Công thức F23: throughput=N/seconds; estimated time=chunks/throughput

Input và thế số: 32457/1054.6336726; 49063/30.7756151195. Kết quả: 30.775615119 docs/s; 1594.216714 s.

Diễn giải: Thời gian alternate policy là estimate. Loại: DERIVED.

Trace code: scripts/task2_rag_accounting.py. Nguồn: reports/task2/embedding_workload.csv.

### F24 RRF

Công thức F24: RRF(d)=Σ_r 1/(k+rank_r(d))

Input và thế số: EXAMPLE A:1/61+1/64; B:2/62. Kết quả: A=0.032018443; B=0.032258065.

Diễn giải: B nhỉnh hơn trong ví dụ. Loại: THEORY/EXAMPLE.

Trace code: rrf_fuse. Nguồn: src/rag_v2/hybrid.py::rrf_fuse.

### F25 BM25

Công thức F25: score(D,Q)=Σ IDF(q)×f(q,D)(k1+1)/(f(q,D)+k1(1−b+b|D|/avgdl))

Input và thế số: THEORY f=1,k1=1.2,b=.75,|D|=avgdl: multiplier=2.2/2.2. Kết quả: 1.

Diễn giải: SQLite trả negative rank; code đảo dấu; IDF theo FTS5. Loại: THEORY/EXAMPLE.

Trace code: SQL bm25(reviews_fts). Nguồn: src/rag_v2/lexical.py; SQLite documentation.

### F26 Mean reciprocal rank

Công thức F26: MRR=(1/Q)Σ_q 1/rank_q; missing→0

Input và thế số: EXAMPLE (1+1/4+0)/3. Kết quả: 0.416667.

Diễn giải: Chỉ relevant đầu tiên. Loại: THEORY/EXAMPLE.

Trace code: known_positive_scores. Nguồn: src/rag/evaluation.py::known_positive_scores.

### F27 Mean latency

Công thức F27: L_mean=Σ latency_i/n

Input và thế số: EXAMPLE [100,200,300] ms. Kết quả: 200.

Diễn giải: Phải thống nhất scope retrieval/generation/end-to-end. Loại: THEORY/EXAMPLE.

Trace code: measure_predictions; telemetry. Nguồn: src/baselines/metrics.py; src/rag_v3/service.py.

### F28 Percentile p95

Công thức F28: h=(n−1)×0.95; interpolate sorted x at h

Input và thế số: EXAMPLE [100,200,300]: h=1.9, 200+.9×100. Kết quả: 290.

Diễn giải: Linear interpolation; minh họa không là project latency. Loại: THEORY/EXAMPLE.

Trace code: np.percentile / Series.quantile. Nguồn: src/baselines/metrics.py; numpy/pandas default.

### F29 Review vượt 128 tokens

Công thức F29: rate = n_exceed / n_docs ×100

Input và thế số: 11235/32457×100. Kết quả: 34.615029.

Diễn giải: Material embedding truncation limitation. Loại: DERIVED.

Trace code: scripts/task2_rag_accounting.py::policy_measure. Nguồn: reports/task2/chunking_comparison.csv.

### F30 V1 test token usage

Công thức F30: total=input+output; mean=total/N

Input và thế số: 249190+6210=255400; 255400/887. Kết quả: 287.936866.

Diễn giải: Không cộng corpus tokenizer totals; gồm protocol request. Loại: DERIVED.

Trace code: src/proposed_v1/runner.py::usage. Nguồn: reports/proposed_v1/qwen_test_metrics.json.

## Tính lại classification từ confusion matrix

Bảng 1. Rule confusion-derived

| Class | TP | FP | FN | P | R | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| negative | 76 | 13 | 208 | 0.853933 | 0.267606 | 0.407507 |
| neutral | 40 | 394 | 3 | 0.092166 | 0.930233 | 0.167715 |
| positive | 332 | 32 | 228 | 0.912088 | 0.592857 | 0.718615 |

Nguồn: reports/baselines/rule_based_test_metrics.json. Loại: DERIVED.

Bảng 2. TF-IDF confusion-derived

| Class | TP | FP | FN | P | R | F1 |
| --- | --- | --- | --- | --- | --- | --- |
| negative | 228 | 78 | 56 | 0.745098 | 0.802817 | 0.772881 |
| neutral | 19 | 30 | 24 | 0.387755 | 0.441860 | 0.413043 |
| positive | 471 | 61 | 89 | 0.885338 | 0.841071 | 0.862637 |

Nguồn: reports/baselines/tfidf_test_metrics.json. Loại: DERIVED.

## Token histogram consistency

minilm_embedding: Σ review_count=32457; Σ tokens_per_review×review_count=3750416; average=115.550297316. Nguồn: reports/task2/rag_token_distribution.csv. DERIVED và đối chiếu JSON: PASS.

qwen2_5_3b_generation: Σ review_count=32457; Σ tokens_per_review×review_count=4105360; average=126.486120097. Nguồn: reports/task2/rag_token_distribution.csv. DERIVED và đối chiếu JSON: PASS.

## Parameter defense notebook

### Quyết định 1 Vì sao chọn Sentiment ngram_range

Định nghĩa và giá trị chọn: Sentiment ngram_range = (1,2). Giữ cụm hai token và chọn trial C_bigram_c2 có macro-F1 validation cao nhất.

Ứng viên và kết quả: (1,1), C=1: val macro-F1 0,648722; (1,2), C=1: 0,700294; (1,2), C=2: 0,709242. Loại selection: VALIDATION_SELECTED.

Nếu tăng hoặc đổi theo hướng lớn hơn: N-gram dài tăng số đặc trưng và sparsity. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Unigram bỏ một phần ngữ cảnh cụm.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/baselines/tfidf_experiments.csv.

### Quyết định 2 Vì sao chọn Sentiment C

Định nghĩa và giá trị chọn: Sentiment C = 2. Nghịch đảo regularization; chọn điểm validation tốt hơn trong hai giá trị.

Ứng viên và kết quả: C=1 và 2 với bigram: 0,700294 và 0,709242. Loại selection: VALIDATION_SELECTED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Regularization yếu hơn, có thể overfit. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Regularization mạnh hơn, có thể underfit.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: src/baselines/tfidf_logreg.py.

### Quyết định 3 Vì sao chọn max_features

Định nghĩa và giá trị chọn: max_features = 20000. Giới hạn kích thước vector và classifier.

Ứng viên và kết quả: Không có sweep vocabulary size. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Giữ thêm từ hiếm nhưng tốn RAM và có thể nhiễu. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Gọn hơn nhưng có thể mất tín hiệu.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/baselines/tfidf_logreg.py.

### Quyết định 4 Vì sao chọn min_df

Định nghĩa và giá trị chọn: min_df = 2. Bỏ token chỉ xuất hiện ở một document train.

Ứng viên và kết quả: Không có đối chứng min_df khác. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Bỏ thêm từ hiếm, có thể mất slang. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Giữ từ hiếm, tăng sparsity/nhiễu.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/baselines/tfidf_logreg.py.

### Quyết định 5 Vì sao chọn sublinear_tf

Định nghĩa và giá trị chọn: sublinear_tf = True. TF=1+ln(count) làm nhẹ tác động từ lặp.

Ứng viên và kết quả: Không có trial False. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Bật: giảm dominance của token lặp. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Tắt: dùng count, lặp nhiều nặng hơn.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/baselines/tfidf_logreg.py.

### Quyết định 6 Vì sao chọn class_weight sentiment

Định nghĩa và giá trị chọn: class_weight sentiment = balanced. Giảm thiên lệch đối với neutral bằng loss weighting.

Ứng viên và kết quả: None → neutral val F1 0,170213; balanced → 0,471910. Loại selection: MEASURED_COMPARISON.

Nếu tăng hoặc đổi theo hướng lớn hơn: Tăng weight neutral có thể tăng recall và FP. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Giảm weight có thể bỏ sót neutral.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/task2/imbalance_comparison.csv.

### Quyết định 7 Vì sao chọn max_iter

Định nghĩa và giá trị chọn: max_iter = 1500. Trần số vòng tối ưu, không phải luôn chạy đủ 1500 vòng.

Ứng viên và kết quả: Không sweep iteration cap. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Cho solver thêm cơ hội hội tụ, tốn thời gian nếu cần. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Dễ dừng trước hội tụ.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/baselines/tfidf_logreg.py.

### Quyết định 8 Vì sao chọn Sentiment solver

Định nghĩa và giá trị chọn: Sentiment solver = lbfgs. Phù hợp objective multinomial của ba lớp.

Ứng viên và kết quả: Không so solver trong accepted baseline. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Không có thứ tự lớn nhỏ; đổi solver cần kiểm penalty/objective. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Không có thứ tự lớn nhỏ; liblinear thuộc OVR aspect riêng.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/baselines/tfidf_logreg.py.

### Quyết định 9 Vì sao chọn Seed

Định nghĩa và giá trị chọn: Seed = 42. Đóng băng protocol; ba seed kiểm độ nhạy training trên cùng split.

Ứng viên và kết quả: So sánh 42,123,2026 cho cùng test macro-F1 0,682854. Loại selection: CONFIGURED_AND_MEASURED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Giá trị số lớn hơn không mang ý nghĩa chất lượng. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Giá trị số nhỏ hơn không mang ý nghĩa chất lượng.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/task2/baseline_three_seed.csv.

### Quyết định 10 Vì sao chọn Aspect C

Định nghĩa và giá trị chọn: Aspect C = 2. C=2 threshold=0,5 có val micro-F1 cao nhất 0,821752.

Ứng viên và kết quả: C=0,5/2 × threshold=0,3/0,5/0,7; bảng sáu trial. Loại selection: VALIDATION_SELECTED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Có thể tăng fit và overfit. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Có thể regularize mạnh quá.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/aspect_classifier/validation_comparison.csv.

### Quyết định 11 Vì sao chọn Aspect threshold

Định nghĩa và giá trị chọn: Aspect threshold = 0.5. Trade-off recall/precision được đo trên validation.

Ứng viên và kết quả: 0,3/0,5/0,7 tại C=2: micro-F1 0,761201/0,821752/0,764747. Loại selection: VALIDATION_SELECTED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Ít nhãn predicted hơn, có thể tăng precision giảm recall. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Nhiều nhãn hơn, tăng recall và FP.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/aspect_classifier/validation_comparison.csv.

### Quyết định 12 Vì sao chọn Chunk policy

Định nghĩa và giá trị chọn: Chunk policy = one review one document. Giữ review-ID/citation/filter nhất quán với artifact đã nghiệm thu.

Ứng viên và kết quả: Mô phỏng 128/0,128/32,256/0,256/32,512/0,512/64; không đánh giá index thay thế. Loại selection: ENGINEERING_WITH_SIMULATION.

Nếu tăng hoặc đổi theo hướng lớn hơn: Chunk lớn giữ context nhưng có truncation. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Chunk nhỏ tăng fragmentation và vector count.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: reports/task2/chunking_comparison.csv.

### Quyết định 13 Vì sao chọn Embedding model

Định nghĩa và giá trị chọn: Embedding model = multilingual MiniLM L12 v2. Chọn recall@10 rồi MRR rồi query latency trên pool.

Ứng viên và kết quả: Pool 612: Potion known recall@10 0,166667; MiniLM 0,333333. Loại selection: DEVELOPMENT_SELECTED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Model lớn hơn cần benchmark mới, không bảo đảm tốt hơn. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Model nhỏ hơn giảm tài nguyên nhưng có thể mất quality.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/rag/embedding_comparison.csv.

### Quyết định 14 Vì sao chọn Embedding dimensions

Định nghĩa và giá trị chọn: Embedding dimensions = 384. Output architecture của MiniLM, không được tune độc lập.

Ứng viên và kết quả: Potion có 256 nhưng là model khác. Loại selection: ARCHITECTURE_FIXED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Đổi dimension cần model/projection và index mới. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Giảm dimension có thể mất thông tin; chưa thử.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag/embeddings.py.

### Quyết định 15 Vì sao chọn top_k

Định nghĩa và giá trị chọn: top_k = 5 demo; 10 retrieval evaluation. Giới hạn evidence ứng viên hiển thị; benchmark cần tới rank 10.

Ứng viên và kết quả: Không sweep 1/3/5/10 để chọn tối ưu demo. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Thêm ứng viên, chi phí và nhiễu; packet vẫn cap 3. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Có thể bỏ evidence hữu ích.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: config/demo.yaml; src/rag_v3/cli.py.

### Quyết định 16 Vì sao chọn Dense và lexical top_n

Định nghĩa và giá trị chọn: Dense và lexical top_n = 20 mỗi nhánh. Đủ pool để fusion trước final top-k.

Ứng viên và kết quả: Không sweep candidate depth. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Tốn truy xuất/rerank và có thể tăng recall. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Nhanh hơn nhưng ít candidate.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v2/hybrid.py.

### Quyết định 17 Vì sao chọn RRF constant

Định nghĩa và giá trị chọn: RRF constant = 60. Fusion theo rank tránh khác scale cosine/BM25.

Ứng viên và kết quả: Không sweep k. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Các top ranks ít phân biệt hơn. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Top ranks ảnh hưởng mạnh hơn.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v2/hybrid.py::rrf_fuse.

### Quyết định 18 Vì sao chọn BM25 k1 và b

Định nghĩa và giá trị chọn: BM25 k1 và b = SQLite FTS5: 1.2 và 0.75. Library-defined frequency saturation và length normalization.

Ứng viên và kết quả: Code chỉ gọi bm25(table), không tune. Loại selection: LIBRARY_DEFAULT.

Nếu tăng hoặc đổi theo hướng lớn hơn: Lý thuyết tăng k1 làm saturation chậm; tăng b tăng length effect. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Giảm k1 saturation nhanh; b=0 bỏ length normalization.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v2/lexical.py; https://www.sqlite.org/fts5.html.

### Quyết định 19 Vì sao chọn Evidence reranking

Định nghĩa và giá trị chọn: Evidence reranking = +0.004 aspect; +0.006/-0.012 polarity; ±0.006 issue. Ưu tiên evidence đúng topic/intent.

Ứng viên và kết quả: Có policy comparison, không sweep riêng từng coefficient. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Rule có thể lấn át score retrieval. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Rule có ảnh hưởng ít hơn.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v2/hybrid.py::search_debug.

### Quyết định 20 Vì sao chọn Evidence packet cap

Định nghĩa và giá trị chọn: Evidence packet cap = 3 review. Giới hạn prompt và khả năng trích dẫn sai.

Ứng viên và kết quả: Không sweep 1/3/5. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Thêm context và nguy cơ trộn facts. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Có thể thiếu coverage.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v3/evidence.py::build_packet.

### Quyết định 21 Vì sao chọn Packet text cap

Định nghĩa và giá trị chọn: Packet text cap = 350 ký tự. Giữ đoạn ngắn và dịch tới complaint cue khi cần.

Ứng viên và kết quả: Không so cap khác. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Thêm context/token. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Có thể cắt mất thông tin hỗ trợ.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v3/evidence.py::_packet_text.

### Quyết định 22 Vì sao chọn LLM demo

Định nghĩa và giá trị chọn: LLM demo = Qwen2.5 3B Q4_K_M. Cải thiện nhỏ ở accepted replay; không thay bởi benchmark contention.

Ứng viên và kết quả: Accepted 1,5B fallback=3; 3B fallback=2 trên sáu ca. Loại selection: LOCAL_ACCEPTANCE_SELECTED.

Nếu tăng hoặc đổi theo hướng lớn hơn: Model lớn hơn tốn RAM/latency, cần đánh giá. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Model nhỏ hơn tiết kiệm nhưng đã fallback nhiều hơn ở replay.

Giới hạn: Chỉ kết luận trong tập ứng viên và protocol đã đo; không chứng minh tối ưu tổng quát.

Nguồn: reports/rag_v3/generation_metrics.json.

### Quyết định 23 Vì sao chọn Quantization

Định nghĩa và giá trị chọn: Quantization = Q4_K_M. Weights đủ nhỏ cho local runtime.

Ứng viên và kết quả: Không có full precision đối chứng. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Nhiều bit có thể tăng quality nhưng tăng memory. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Ít bit hơn có thể mất quality.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: qwen_v1.yaml; qwen_v3_3b.yaml.

### Quyết định 24 Vì sao chọn Temperature

Định nghĩa và giá trị chọn: Temperature = 0. Giảm randomness cho classification và grounded answers.

Ứng viên và kết quả: Không sweep sampling temperature. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Đa dạng hơn nhưng ít ổn định. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Đang ở 0, không giảm dưới miền hợp lệ.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/llm/gateway.py::generate.

### Quyết định 25 Vì sao chọn Context length

Định nghĩa và giá trị chọn: Context length = 2048. Giới hạn KV cache và prompt budget.

Ứng viên và kết quả: Không thử tối ưu context window. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Thêm context nhưng tăng bộ nhớ. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Dễ vượt context hoặc phải cắt prompt.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: qwen_v3_3b.yaml; docker-compose.yml.

### Quyết định 26 Vì sao chọn Output token cap

Định nghĩa và giá trị chọn: Output token cap = 32 sentiment; 128 V3. Đủ cho JSON label hoặc câu ngắn; giới hạn chi phí.

Ứng viên và kết quả: Không sweep cap; DeepSeek structured output thất bại dưới 128. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Có thể đủ diễn đạt hơn nhưng tăng latency. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Có thể cắt JSON/câu chưa hoàn chỉnh.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: qwen_v1.yaml; src/rag_v3/service.py.

### Quyết định 27 Vì sao chọn Attempts

Định nghĩa và giá trị chọn: Attempts = 2. Một lần sửa instruction rồi fallback.

Ứng viên và kết quả: Không có retry budget comparison. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Tăng thời gian và tài nguyên worst case. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Ít cơ hội sửa schema/support.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/rag_v3/service.py.

### Quyết định 28 Vì sao chọn CPU threads

Định nghĩa và giá trị chọn: CPU threads = 8 local config. Chọn mức song song vừa phải.

Ứng viên và kết quả: Host 16 logical CPUs được nêu; không benchmark thread count. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Có thể contention hoặc nhanh hơn, cần đo. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Có thể chậm hơn và giảm tranh chấp.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: qwen_v1.yaml; qwen_v3_3b.yaml.

### Quyết định 29 Vì sao chọn GPU layers

Định nghĩa và giá trị chọn: GPU layers = 99 requested; Docker CPU observed. Yêu cầu offload không chứng minh offload thực xảy ra.

Ứng viên và kết quả: Local launcher -CpuOnly đổi thành 0; Compose không khai báo GPU device. Loại selection: CONFIGURED_WITH_LIMIT.

Nếu tăng hoặc đổi theo hướng lớn hơn: Chỉ có tác dụng khi runtime/device hỗ trợ và đủ VRAM. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Ít offload giảm VRAM nhưng có thể chậm.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md.

### Quyết định 30 Vì sao chọn Ports

Định nghĩa và giá trị chọn: Ports = 8501 UI; 8000 API; 8193 Compose Qwen; 8194 local 3B. Tách service endpoints; URL override xác định đúng runtime.

Ứng viên và kết quả: Không có bài toán quality optimization của port. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Đổi số cần đồng bộ client/firewall; không tăng quality. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Tương tự; tránh port đang dùng.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: docker-compose.yml; qwen_v3_3b.yaml.

### Quyết định 31 Vì sao chọn Mount permissions

Định nghĩa và giá trị chọn: Mount permissions = models/reports RO; data/state RW. Bảo vệ weights/report, cho state logging và data access.

Ứng viên và kết quả: Không benchmark permission; là deployment contract. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Quyền ghi rộng hơn tăng nguy cơ sửa artifact. Nếu giảm hoặc đổi theo hướng nhỏ hơn: RO toàn bộ có thể chặn state update.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: docker-compose.yml.

### Quyết định 32 Vì sao chọn Alert thresholds

Định nghĩa và giá trị chọn: Alert thresholds = n≥10; rate delta≥0.2; rating delta≤−1.0. Loại kỳ quá ít mẫu và hiển thị biến động lớn.

Ứng viên và kết quả: Không có threshold calibration trên gold alerts. Loại selection: ENGINEERING.

Nếu tăng hoặc đổi theo hướng lớn hơn: Tăng minimum/delta giảm số alert. Nếu giảm hoặc đổi theo hướng nhỏ hơn: Giảm minimum/delta có thể tăng nhiễu.

Giới hạn: Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu.

Nguồn: src/foody/analytics.py::alerts.
