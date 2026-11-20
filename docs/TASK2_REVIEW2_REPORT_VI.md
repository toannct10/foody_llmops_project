# End-to-End Food Review Intelligence & LLMOps Platform

Báo cáo học thuật Task 2 Review 2

End-to-End Food Review Intelligence & LLMOps Platform

Ngày lập tài liệu 22/10/2026. Source snapshot 4229a8b3998392c97f4b7a8c9e3795830285dbce.

Nhóm thực hiện: [Điền tên nhóm và thành viên]. Giảng viên: [Điền họ tên]. Học phần/lớp: [Điền thông tin].

Tài liệu phân biệt MEASURED (đo đã lưu), DERIVED (tính lại), CONFIGURED (tham số code/config), EXTERNAL (nguồn ngoài). THEORY và EXAMPLE không phải kết quả project. Các đường dẫn source tính từ thư mục gốc repository.

<!-- TOC -->

## Tóm tắt điều hành

Nghiên cứu xây dựng hệ thống phân tích review nhà hàng tiếng Việt và phục vụ hỏi đáp có bằng chứng. VN-MSASar v3 cung cấp5869 dòng câu–aspect với split4140/842/887; Foody first-party cung cấp33946 dòng nguồn,32457 review hợp lệ riêng biệt và2110 nhà hàng cho inference/RAG. TF-IDF LR đạt test macro-F1 0,682854, cao hơn rule0,431279 và Qwen V1 0,621789, nên được giữ cho phân loại. RAG V3 dùng routing, Chroma/BM25, packet, Qwen3B và validator/fallback. Sáu ca replay cho2 supported complete,1 incomplete,3 correct insufficient và0 validator-detected unsupported accepted. Docker local và image delivery GHCR đã xác minh; không claim production deployment hoặc LLM training from scratch.

## 1 Bài toán và phạm vi

Người quản lý nhà hàng cần biết khách đang khen hoặc phàn nàn điều gì, tại chi nhánh nào và trong khoảng thời gian nào. Khi hàng nghìn nhận xét nằm rải rác trong file xuất, đọc từng dòng khó tạo được một bức tranh nhất quán. Hệ thống chuẩn hóa dữ liệu, bổ sung dự đoán sentiment và aspect, tạo bảng tổng hợp, rồi cho phép hỏi bằng tiếng Việt với bằng chứng review đi kèm.

Nguồn: README.md; src/foody/pipeline.py; app/app.py; reports/task2/TRAINING_SCOPE.md.

In scope: benchmark text-only, classifier aspect, Foody inference/marts, local RAG V3, UI, telemetry, Docker/CI/CD evidence. Out of scope: full LLM training from scratch, production remote rollout, Foody gold accuracy và thay đổi artifact đã đóng băng.

## 2 Nguồn dữ liệu

Nguồn public là phamluan/vn_msa_sar_v3 trên Hugging Face, revision 6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4, license CC BY 4.0 theo provenance. Ba file nguồn có tổng 76.785 dòng. Adapter chỉ giữ language=vi và place_type=restaurant, còn 5.869 dòng hợp lệ; không có dòng bị reject hoặc duplicate bị loại ở lần chuẩn bị đã lưu.

Nguồn: reports/food_dataset_report.json; src/food/adapters.py; data/food/source/vn_msasar_v3/provenance.json.

Nguồn demo hiện hành là data/foody/source/foody_reviews.csv, không phải review.csv lịch sử. First-party ownership là thông tin người dùng cung cấp; checksum chỉ chứng minh snapshot trùng byte, không tự chứng minh quyền sở hữu hoặc tính đại diện. Có 33.946 dòng thô, 33.938 dòng hợp lệ cho AI, 31.694 observation suy luận sau gộp và 32.457 review_id hợp lệ riêng biệt, thuộc 2.110 restaurant_key.

Một observation gộp restaurant_key với text chuẩn hóa để tránh dự đoán lặp. Một review_id còn gồm User, thời gian thô và Comment gốc, vì vậy các người/ngày khác nhau có thể chia sẻ một lần suy luận nhưng vẫn là review khác. Marts/RAG dùng distinct review_id; processed/enriched giữ tất cả source rows. restaurant_key tạo từ tên chuẩn hóa, không phải official ID; trùng tên chi nhánh vẫn là rủi ro.

Nguồn: src/foody/cleaning.py; src/foody/schema.py; reports/foody_intelligence/cleaning.json.

Bảng 1. Dataset source registry

| source | origin | access | raw_rows |
| --- | --- | --- | --- |
| VN-MSASar v3 | https://huggingface.co/datasets/phamluan/vn_msa_sar_v3 | public offline pinned revision | 76785 |
| First-party Foody crawl | data/foody/source/foody_reviews.csv | first-party local export; no public URL documented | 33946 |

Nguồn: reports/task2/dataset_sources.csv. Loại: MEASURED.

Bảng 2. Các đơn vị đếm Foody

| Trường | Giá trị |
| --- | --- |
| raw_rows | 33946 |
| valid_ai_rows | 33938 |
| deduplicated_ai_observations | 31694 |
| distinct_valid_review_ids | 32457 |
| restaurant_count | 2110 |
| date_range | ["2011-01-09 12:07:32", "2026-10-14 15:46:56"] |
| rating_range | [0.0, 10.0] |
| missing_ratings | 0 |

Nguồn: reports/foody_intelligence/cleaning.json. Loại: MEASURED.

## 3 Làm sạch và gán nhãn

Thang sentiment nguồn là số nguyên từ −3 đến +3. Hàm ordinal kiểm tra số hữu hạn, nguyên và nằm trong tập cho phép; boolean, NaN hoặc giá trị ngoài miền bị loại. LABEL_MAPPING ánh xạ số âm thành negative, 0 thành neutral và số dương thành positive. Đây là phép gộp độ mạnh theo dấu, không phải chuyển rating sao thành sentiment.

Nguồn: src/food/adapters.py::ordinal và LABEL_MAPPING; reports/food_label_mapping.json.

VN-MSASar labels do dataset cung cấp; không có annotation nhiều người mới hoặc Kappa của nhóm nên Kappa=N/A. Foody hiện hành không có Classification; rating giữ vai trò metadata. NFC/whitespace giữ dấu, case và nguồn gốc. Loại khỏi AI không đồng nghĩa xóa source row. Các export review.csv cũ là supplementary historical evidence.

## 4 Train validation test và leakage

Train dùng để fit vocabulary, IDF và trọng số classifier. Validation chọn cấu hình/prompt. Test chỉ đánh giá cấu hình đã đóng băng. Đưa một phần câu test vào quá trình fit làm mô hình biết trước đặc điểm tập đánh giá và tạo ước lượng lạc quan.

assign_splits không chia từng dòng độc lập: leakage_groups dùng thành phần liên thông nối các dòng chung review_id hoặc text chuẩn hóa. Vì thế một review hoặc câu giống hệt không đi vào nhiều split. Thuật toán tìm 64 phương án GroupShuffleSplit theo seed 42 rồi chọn phương án gần tỷ lệ và phân bố lớp mong muốn; đây là tìm split bằng nhãn, không phải chọn theo điểm dự đoán test. Tỷ lệ thực không đúng tuyệt đối 70/15/15 do ràng buộc nhóm.

Nguồn: src/food/split.py::leakage_groups, assign_splits, load_splits; data/food/splits/metadata.json.

Split SHA256: 860387be19c64220f91cc2b5e764aa3c99aa18daba9c776fde38e05da30a5ff9

Bảng 3. Split và số đếm

| Split | Rows | Review IDs | Negative | Neutral | Positive |
| --- | --- | --- | --- | --- | --- |
| train | 4140 | 1074 | 1307 | 208 | 2625 |
| validation | 842 | 229 | 270 | 43 | 529 |
| test | 887 | 227 | 284 | 43 | 560 |

Nguồn: data/food/splits/metadata.json. Loại: MEASURED.

## 5 Mất cân bằng lớp

Positive chiếm 3.714 dòng, negative 1.861 và neutral 294. Class imbalance nghĩa là số ví dụ giữa các lớp chênh lệch; mô hình có thể ưu tiên lớp đông và vẫn có accuracy khá. Vì thế macro-F1, lấy trung bình công bằng theo lớp, phù hợp để chọn sentiment classifier trong project.

Nguồn: reports/task2/class_distribution.csv; reports/food_dataset_report.json.

Balanced weight tăng chi phí của lỗi ở lớp ít ví dụ. Với N=4.140 và K=3, weight_j=N/(K×n_j). Train negative=1.307 cho weight 1,055853; neutral=208 cho 6,634615; positive=2.625 cho 0,525714. Các giá trị được tính lại bằng script tài liệu, không chỉnh training.

Validation cho thấy neutral recall tăng từ 0,093023 lên 0,488372 và neutral F1 tăng từ 0,170213 lên 0,471910 khi dùng balanced. Precision neutral giảm từ 1 xuống 0,456522: mô hình tìm thêm neutral nhưng cũng tạo false positives. Đây là trade-off có đo đạc, không phải lời khẳng định mọi lớp đều tốt hơn.

Nguồn: src/baselines/tfidf_logreg.py; reports/task2/imbalance_comparison.csv.

Bảng 4. Ảnh hưởng class weight

| Weight mode | Class | Weight | Val P | Val R | Val F1 |
| --- | --- | --- | --- | --- | --- |
| None | negative | 1 | 0.813230 | 0.774074 | 0.793169 |
| None | neutral | 1 | 1 | 0.093023 | 0.170213 |
| None | positive | 1 | 0.839931 | 0.922495 | 0.879279 |
| balanced | negative | 1.055853 | 0.750000 | 0.833333 | 0.789474 |
| balanced | neutral | 6.634615 | 0.456522 | 0.488372 | 0.471910 |
| balanced | positive | 0.525714 | 0.895161 | 0.839319 | 0.866341 |

Nguồn: reports/task2/imbalance_comparison.csv. Loại: MEASURED.

![Validation trước và sau balanced weights](../reports/task2/figures/imbalance_effect.png)

Hình 1. Validation trước và sau balanced weights. Nguồn: reports/task2/figures/imbalance_effect.png.

## 6 Chuẩn bị dữ liệu RAG

foody_reviews.csv → immutable snapshot → processed giữ source_row/original text → grouped observations → sentiment/aspect inference → issue rules → enriched join lại mọi dòng → distinct-review marts → documents.jsonl → embedding/Chroma và FTS5/BM25. Mỗi chuyển đổi có hash/manifest hoặc report để theo lineage.

Nguồn: src/foody/cleaning.py; src/foody/enrichment.py; src/foody/analytics.py; src/foody/pipeline.py.

## 7 Baselines

VietnameseRuleBased tách token và dấu câu; khớp cụm lexicon dài nhất không chồng lấp. Từ/cụm tích cực đóng góp +1, tiêu cực −1. Số lượng phủ định lẻ trong ba token trước đảo dấu; punctuation hoặc từ đối lập kết thúc phạm vi. Intensifier nhân đóng góp với 1,5. Tổng dương → positive, âm → negative, bằng 0 → neutral.

Nguồn: src/baselines/rule_based.py; reports/baselines/rule_based_test_metrics.json.

Rule-Based đạt test accuracy 0,505073, macro-F1 0,431279. TF-IDF LR đạt 0,809470 và 0,682854. TF-IDF neutral F1 là 0,413043, vẫn yếu hơn negative/positive. Accuracy cao hơn chưa đủ; macro-F1 và per-class report xác nhận cải thiện có ý nghĩa đối với mục tiêu ba lớp.

Nguồn: reports/baselines/baseline_comparison.csv; reports/task2/FEASIBILITY.csv; src/foody/enrichment.py.

Bảng 5. Chọn cấu hình sentiment trên validation

| Trial | Ngrams | C | Val accuracy | Val macro F1 |
| --- | --- | --- | --- | --- |
| A_unigram_c1 | (1, 1) | 1 | 0.767221 | 0.648722 |
| B_bigram_c1 | (1, 2) | 1 | 0.812352 | 0.700294 |
| C_bigram_c2 | (1, 2) | 2 | 0.819477 | 0.709242 |

Nguồn: reports/baselines/tfidf_experiments.csv. Loại: MEASURED.

Bảng 6. Sentiment test metrics cùng frozen split

| Model | Accuracy | Macro P | Macro R | Macro F1 | Weighted F1 |
| --- | --- | --- | --- | --- | --- |
| Rule | 0.505073 | 0.619395 | 0.596898 | 0.431279 | 0.592298 |
| TF-IDF LR | 0.809470 | 0.672730 | 0.695250 | 0.682854 | 0.812104 |
| Qwen V1 | 0.732807 | 0.632795 | 0.733282 | 0.621789 | 0.774715 |
| Qwen V2-A exploratory | 0.723788 | 0.646854 | 0.728008 | 0.614487 | 0.778542 |

Nguồn: reports/baselines/*test_metrics.json; reports/proposed_v1/qwen_test_metrics.json; reports/proposed_v2/test_metrics.json. Loại: MEASURED.

![Baseline và proposed sentiment](../reports/task2/figures/baseline_comparison.png)

Hình 2. Baseline và proposed sentiment. Nguồn: reports/task2/figures/baseline_comparison.png.

## 8 Độ ổn định ba seed

Seed điều khiển các bước ngẫu nhiên; không phải mọi solver đều nhạy với seed. Ba lần train so sánh dùng seed 42, 123, 2026 trên cùng frozen membership và cùng cấu hình đã chấp nhận. Artifact classifier demo không bị ghi đè bởi nghiên cứu này.

Nguồn: reports/task2/baseline_three_seed.csv; reports/task2/linearsvc_validation_selection.csv; scripts/task2_classical_comparison.py.

Bảng 7. Ba seed trên cùng membership

| Seed | Split | Accuracy | Macro F1 | Weighted F1 | Neutral F1 |
| --- | --- | --- | --- | --- | --- |
| 42 | validation | 0.819477 | 0.709242 | 0.821549 | 0.471910 |
| 42 | test | 0.809470 | 0.682854 | 0.812104 | 0.413043 |
| 123 | validation | 0.819477 | 0.709242 | 0.821549 | 0.471910 |
| 123 | test | 0.809470 | 0.682854 | 0.812104 | 0.413043 |
| 2026 | validation | 0.819477 | 0.709242 | 0.821549 | 0.471910 |
| 2026 | test | 0.809470 | 0.682854 | 0.812104 | 0.413043 |

Nguồn: reports/task2/baseline_three_seed.csv. Loại: MEASURED.

Bảng 8. LinearSVC supplemental selection

| C | Val accuracy | Val macro F1 | Val neutral F1 |
| --- | --- | --- | --- |
| 0.500000 | 0.836105 | 0.701795 | 0.424242 |
| 1 | 0.830166 | 0.692742 | 0.412698 |
| 2 | 0.828979 | 0.689493 | 0.406250 |

Nguồn: reports/task2/linearsvc_validation_selection.csv. Loại: MEASURED.

## 9 Paper và kết quả nhóm

Không có baseline paper tái lập với cùng filtered dataset, label normalization, input và887-row test. Rule lexicon do nhóm xây; LR/SVC là implementation sklearn. Dataset/model/method documentation không cung cấp một paper macro-F1 tương đương. Vì vậy numerical paper–group gap=N/A và NOT DIRECTLY COMPARABLE. Hoàn thành checklist mục này có nghĩa hoàn thành source audit, không chứng minh replication thành công.

Bảng 9. Kết quả nhóm không phải điểm paper

| Local model | Group accuracy | Group macro F1 |
| --- | --- | --- |
| Rule-based | 0.505073 | 0.431279 |
| TF-IDF + Logistic Regression | 0.809470 | 0.682854 |
| TF-IDF + LinearSVC | 0.818489 | 0.667210 |

Nguồn: reports/task2/classical_model_comparison.csv. Loại: MEASURED.

## 10 Gap analysis

V1 sai 237/887 mẫu; TF-IDF sai 169. Neutral V1 recall 0,674419 nhưng precision chỉ 0,159341: mô hình bắt được 29/43 gold-neutral nhưng dự đoán neutral quá nhiều. F1 0,257778 thấp hơn TF-IDF 0,413043. Không thể dùng recall đơn lẻ để tuyên bố neutral được cải thiện.

failure_counts cho sarcasm 9 lỗi trên 37 mẫu, mixed-marker 45/121, negation-marker 42/208, short text 33/93 và conflicting text 16/24. Các nhóm chồng lấp; chỉ sarcasm lấy nhãn nguồn, các marker khác là proxy lexical. Không cộng các tử số thành tổng lỗi và không coi proxy là annotation thủ công về hiện tượng ngôn ngữ.

Nguồn: reports/task2/failure_counts.csv; reports/proposed_v1/qwen_test_metrics.json; reports/baselines/tfidf_classification_report.csv.

Research gap xác minh: neutral ít và text-only không biểu diễn aspect ambiguity. Domain shift/hyperparameter/pretraining là giả thuyết chưa được isolate. Hướng cải thiện được kiểm bằng prompt calibration và aspect input; RAG V3 giải quyết grounding demo, không nâng sentiment macro-F1 của classifier.

## 11 Proposed V1

V1 dùng Qwen2.5-1.5B-Instruct-GGUF Q4_K_M, chạy llama.cpp b11429. Model là bộ trọng số đã tiền huấn luyện; runtime là phần mềm thực thi trọng số. GGUF là định dạng; Q4_K_M là cấu hình quantization hỗn hợp trong họ K-quant, không phải mọi tensor đều chính xác bốn bit. Không có fine-tuning hoặc training LLM from scratch.

Ba prompt đóng băng: v1_a tối giản, v1_b định nghĩa nhãn, v1_c thêm ba ví dụ train-only không xung đột. Chọn bằng validation macro-F1, rồi JSON validity và latency. Qwen chỉ nhận text, phải trả JSON sentiment thuộc ba nhãn. Temperature=0, seed=42, output cap=32, tối đa hai attempts; parser/schema không âm thầm đổi free text thành label.

Nguồn: qwen_v1.yaml; src/proposed_v1/runner.py; reports/proposed_v1/qwen_prompt_comparison.csv; reports/proposed_v1/qwen_resource_report.json.

Bảng 10. Prompt V1 selection

| Prompt | Val macro F1 | JSON rate | Mean ms | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- |
| v1_a | 0.589172 | 1 | 66.254108 | 79349 | 5894 |
| v1_b | 0.626862 | 1 | 75.553218 | 152603 | 5894 |
| v1_c | 0.641252 | 1 | 93.411746 | 237645 | 5894 |

Nguồn: reports/proposed_v1/qwen_prompt_comparison.csv. Loại: MEASURED.

## 12 Failure analysis

V1 sai 237/887 mẫu; TF-IDF sai 169. Neutral V1 recall 0,674419 nhưng precision chỉ 0,159341: mô hình bắt được 29/43 gold-neutral nhưng dự đoán neutral quá nhiều. F1 0,257778 thấp hơn TF-IDF 0,413043. Không thể dùng recall đơn lẻ để tuyên bố neutral được cải thiện.

failure_counts cho sarcasm 9 lỗi trên 37 mẫu, mixed-marker 45/121, negation-marker 42/208, short text 33/93 và conflicting text 16/24. Các nhóm chồng lấp; chỉ sarcasm lấy nhãn nguồn, các marker khác là proxy lexical. Không cộng các tử số thành tổng lỗi và không coi proxy là annotation thủ công về hiện tượng ngôn ngữ.

Nguồn: reports/task2/failure_counts.csv; reports/proposed_v1/qwen_test_metrics.json; reports/baselines/tfidf_classification_report.csv.

Bảng 11. Failure taxonomy và mẫu số

| Model | Nhóm lỗi | Errors | Denominator |
| --- | --- | --- | --- |
| rule | negative → neutral | 179 | 887 |
| rule | negative → positive | 29 | 887 |
| rule | neutral → positive | 3 | 887 |
| rule | positive → negative | 13 | 887 |
| rule | positive → neutral | 215 | 887 |
| tfidf | negative → neutral | 9 | 887 |
| tfidf | negative → positive | 47 | 887 |
| tfidf | neutral → negative | 10 | 887 |
| tfidf | neutral → positive | 14 | 887 |
| tfidf | positive → negative | 68 | 887 |
| tfidf | positive → neutral | 21 | 887 |
| Qwen V1 | sarcasm_gold | 9 | 37 |
| Qwen V1 | mixed_marker_proxy | 45 | 121 |
| Qwen V1 | negation_marker_proxy | 42 | 208 |
| Qwen V1 | no_obvious_polarity_word_proxy | 200 | 630 |
| Qwen V1 | neutral_gold | 14 | 43 |
| Qwen V1 | long_text_200plus_chars | 0 | 20 |
| Qwen V1 | short_text_20orless_chars | 33 | 93 |
| Qwen V1 | conflicting_gold_text | 16 | 24 |
| RAG V3 qwen_1_5b | unsupported_clause | 2 | 6 |
| RAG V3 qwen_1_5b | topic_mismatch | 4 | 6 |
| RAG V3 qwen_3b | unsupported_clause | 5 | 5 |

Nguồn: reports/task2/failure_counts.csv. Loại: MEASURED.

## 13 Proposed V2

V2-A vẫn text-only. Ba prompt v2_a1/a2/a3 dùng 6/9/8 ví dụ train, hiệu chỉnh cách hiểu neutral và các trường hợp sai ở validation V1. Chọn v2_a3 bằng validation macro-F1 0,632579. Test macro-F1 0,614487 và neutral F1 0,247104 đều thấp hơn V1 và TF-IDF. Vì test V1 đã được xem, kết quả V2 phải ghi exploratory reused test.

V2-B ở src/aspect_conditioned là protocol khác: text+aspect. Qwen text+aspect test macro-F1 0,602203; TF-IDF text+aspect 0,665514. Không được gọi V2-A là aspect-conditioned như một câu trong GAP_ANALYSIS/Q&A cũ. Hai protocol cần cột input riêng và không được dùng kết quả này làm benchmark text-only công bằng tuyệt đối.

Nguồn: qwen_v2.yaml; qwen_aspect.yaml; reports/proposed_v2/prompt_comparison.csv; reports/aspect_conditioned/comparison.csv.

V2-A và V2-B phải tách tên: text-only calibration so với text+aspect research. Cả hai tái sử dụng test đã xem, không là xác nhận held-out độc lập. Không thay sentiment production artifact.

Bảng 12. V2 A calibration

| Prompt | Train examples | Val macro F1 | Val neutral F1 | Mean ms |
| --- | --- | --- | --- | --- |
| v2_a1 | 6 | 0.623801 | 0.274194 | 110.991605 |
| v2_a2 | 9 | 0.623353 | 0.271493 | 135.550636 |
| v2_a3 | 8 | 0.632579 | 0.283019 | 287.467406 |

Nguồn: reports/proposed_v2/prompt_comparison.csv. Loại: MEASURED.

![V1 và V2 sentiment](../reports/task2/figures/v1_v2_sentiment_comparison.png)

Hình 3. V1 và V2 sentiment. Nguồn: reports/task2/figures/v1_v2_sentiment_comparison.png. Test V2 reused và exploratory.

## 14 RAG V1 V2 V3

V1 dùng selected MiniLM và Chroma full index. Trong shared V3 policy run, recall trên known-positive tại 5=0, tại 10=0,083333, MRR=0,018519, mean retrieval=16,519117 ms. Các số này phải ghi đúng run; bảng V2 candidate có mean 15,761 ms là một lần đo khác.

Nguồn: reports/rag_v3/retrieval_policies.csv; src/rag/service.py; reports/task2/RAG_ABLATION_FINAL.md.

V2 thử dense, BM25, RRF, RRF+expansion và evidence reranking. Expansion thêm các term theo intent đã giới hạn; auto_filter có thể thêm negative và aspect khi câu hỏi là complaint. Rerank cộng hoặc trừ các trọng số nhỏ dựa trên aspect, compatibility và issue matches, không phải neural cross-encoder.

Nguồn: src/rag_v2/hybrid.py; src/rag_v2/service.py; reports/rag_v2/retrieval_candidates.csv.

route_query nhận dạng causal, complaint có aspect, general aspect hoặc summary. Complaint có aspect đi filtered BM25 kèm evidence rerank; general đi hybrid RRF. TREND_CAUSATION đi MART_TREND_GUARD và search_debug trả danh sách rỗng để không suy diễn nguyên nhân từ vài review. Tên guard không có nghĩa query handler luôn chạy một phép phân tích nhân quả trên mart.

build_packet giữ evidence hợp intent/polarity/topic, dedup text và lấy tối đa ba review. Qwen chỉ nhận packet này. attach_citation có thể gắn placeholder bằng overlap khi thiếu inline citation, nhưng sau đó vẫn phải qua validator. Tối đa hai lần sinh; không qua thì extractive_answer, không có evidence thì insufficient.

Nguồn: src/rag_v3/routing.py; src/rag_v3/retriever.py; src/rag_v3/evidence.py; src/rag_v3/service.py.

Bảng 13. Retrieval policy measurements

| policy | known_hit_at_5 | known_hit_at_10 | known_mrr | mean_latency_ms | p95_latency_ms |
| --- | --- | --- | --- | --- | --- |
| RAG_V2_BM25 | 0.083333 | 0.083333 | 0.166667 | 240.010817 | 620.717600 |
| RAG_V1_DENSE | 0 | 0.083333 | 0.018519 | 16.519117 | 21.181625 |
| RAG_V2_RRF | 0.083333 | 0.083333 | 0.041667 | 120.094883 | 162.247875 |
| RAG_V2_EVIDENCE_RERANK | 0.083333 | 0.083333 | 0.055556 | 600.290550 | 1742.720075 |
| RAG_V3_ROUTED | 0.083333 | 0.083333 | 0.166667 | 140.970200 | 195.149225 |

Nguồn: reports/rag_v3/retrieval_policies.csv. Loại: MEASURED.

Chú thích: các cột known_hit lưu macro known-positive recall theo known_positive_scores; không phải binary Hit. Không gộp latency giữa hai run.

## 15 Quyết định chunking

prepare_rag lọc valid_for_ai có prediction và drop_duplicates(review_id), tạo JSONL với id, text, metadata. Index được chấp nhận chứa 32.457 document và vector tương ứng. Chính sách này giúp review_id–citation và filter restaurant nhất quán, không gộp review của nhà hàng khác.

Giới hạn quan trọng: MiniLM runtime được ghi nhận truncation 128 token. Có 11.235 review, tức 34,615029%, dài hơn 128 content tokens; phần đuôi có thể không ảnh hưởng embedding dù BM25 và evidence còn full text. Mean=115,550297, median=92, p95=288, max=2.124 token. 2.239 review vượt 256 và 222 vượt 512.

Nguồn: src/foody/pipeline.py::prepare_rag; reports/task2/rag_token_statistics.json; reports/task2/chunking_comparison.csv.

Bảy policy được mô phỏng trên độ dài token thực, giữ ranh giới review và metadata. 128/0 tạo 46.968 chunks; 128/32 tạo 49.063; 256/0 tạo 34.962; 256/32 tạo 35.057; 512/0 tạo 32.688; 512/64 tạo 32.692. Overlap tăng workload nhưng không tạo thêm review gốc.

Nguồn: reports/task2/chunking_comparison.csv; reports/task2/embedding_workload.csv.

Bảng 14. Simulation chunk workload

| Policy | Chunks | Review split | Overlap tokens | Estimated seconds |
| --- | --- | --- | --- | --- |
| one_review_one_document | 32457 | 0 | 0 | 1054.633673 |
| max_128_overlap_0 | 46968 | 11235 | 0 | 1526.143338 |
| max_128_overlap_32 | 49063 | 11235 | 531392 | 1594.216714 |
| max_256_overlap_0 | 34962 | 2239 | 0 | 1136.029284 |
| max_256_overlap_32 | 35057 | 2239 | 83200 | 1139.116143 |
| max_512_overlap_0 | 32688 | 222 | 0 | 1062.139615 |
| max_512_overlap_64 | 32692 | 222 | 15040 | 1062.269588 |

Nguồn: reports/task2/chunking_comparison.csv. Loại: DERIVED simulation; one-review reference MEASURED.

Bảng 15. Mean content tokens mỗi chunk theo simulation

| Policy | Mean chunk tokens | Rủi ro / storage |
| --- | --- | --- |
| one_review_one_document | 115.550297 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |
| max_128_overlap_0 | 79.850451 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |
| max_128_overlap_32 | 87.271630 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |
| max_256_overlap_0 | 107.271209 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |
| max_256_overlap_32 | 109.353795 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |
| max_512_overlap_0 | 114.733725 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |
| max_512_overlap_64 | 115.179738 | Nhiều chunks hơn tăng vector/metadata; retrieval quality chưa đo |

Nguồn: rag_token_statistics.json + chunking_comparison.csv. Loại: DERIVED.

Bảng 16. Token statistics không truncation

| Tokenizer | Total | Mean | Median | p95 | Max |
| --- | --- | --- | --- | --- | --- |
| minilm_embedding | 3750416 | 115.550297 | 92.000000 | 288.000000 | 2124 |
| qwen2_5_3b_generation | 4105360 | 126.486120 | 101.000000 | 315.000000 | 2249 |

Nguồn: reports/task2/rag_token_statistics.json. Loại: MEASURED.

![Phân bố token trên corpus Foody](../reports/task2/rag_token_distribution.png)

Hình 4. Phân bố token trên corpus Foody. Nguồn: reports/task2/rag_token_distribution.png.

## 16 Embedding và vector database

Embedding ánh xạ text sang vector số để so sánh gần nhau theo biểu diễn học được. EXAMPLE: “phục vụ chậm” và “đem món quá lâu” có thể gần nhau hơn hai câu không liên quan; đó là minh họa ý nghĩa semantic, không phải điểm similarity đã đo của project.

Nguồn: src/rag/embeddings.py; reports/rag/embedding_selection.json; model card Sentence Transformers.

Có một so sánh nhỏ thật, không phải không có benchmark. Pool 612 documents gồm 600 mẫu ngẫu nhiên và known-positive IDs, sáu câu hỏi. Potion multilingual 256 chiều có known-positive recall@10=0,166667, MRR=0,104167; MiniLM 384 chiều có 0,333333 và 0,333333. Quy tắc chọn recall@10 rồi MRR rồi query time chọn MiniLM.

Potion nhanh hơn nhiều trong đo pool nhưng chất lượng theo nhãn dương đã biết thấp hơn. Pool nhỏ và labels chưa đầy đủ; không có exhaustive embedding model benchmark. Chọn MiniLM trong hai ứng viên không chứng minh thắng mọi encoder hoặc tối ưu với full index. Full-index metric giảm so với pool là điều cần giải thích vì không gian cạnh tranh tăng.
Nguồn: src/rag/evaluation.py::compare_candidates; reports/rag/embedding_comparison.csv.

Nguồn: src/rag/evaluation.py::compare_candidates; reports/rag/embedding_comparison.csv.

Chroma lưu collection persistent với cosine HNSW. id của vector bằng review_id; metadata gồm restaurant_key/name, timestamp, raw_rating, predicted_sentiment, aspects/issues dạng JSON và Boolean aspect_<name>. open_collection kiểm tra count bằng manifest trước khi dùng.

Nguồn: src/rag/vector_store.py; src/rag/retriever.py; reports/task2/RAG_METADATA_SCHEMA.md.

Bảng 17. Embedding selection pool612

| Model | Dim | KP recall10 | MRR | Query embed ms |
| --- | --- | --- | --- | --- |
| minishlab/potion-multilingual-128M | 256 | 0.166667 | 0.104167 | 0.223617 |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | 0.333333 | 0.333333 | 3.209650 |

Nguồn: reports/rag/embedding_comparison.csv. Loại: MEASURED.

## 17 Đánh giá retrieval

THEORY: Hit@k(q)=1 nếu top-k có ít nhất một relevant document, ngược lại 0; mean Hit@k lấy trung bình trên query. EXAMPLE: ba query có hit [1,0,1] thì Hit@k=2/3. Đây là chỉ số có hoặc không có, không chia số hit cho số gold của từng query.

Nguồn: src/rag/evaluation.py::known_positive_scores; scripts/evaluate_rag_v3_retrieval.py; reports/rag_v3/retrieval_policy_rows.csv.

MRR nhìn vị trí relevant đầu tiên: query có rank r góp 1/r, không tìm thấy góp 0. MRR là trung bình qua mọi query. EXAMPLE: ranks 1,4,missing cho (1+0,25+0)/3=0,416667. MRR không biết có bao nhiêu relevant khác phía sau.

Nguồn: src/rag/evaluation.py; reports/rag_v3/retrieval_policy_rows.csv.

Recall@k(q)=số relevant retrieved trong top-k / tổng số relevant của query. Full recall đòi hỏi biết đầy đủ tập relevant. Project chỉ có các known-positive IDs do người xây benchmark chọn, vì vậy các số recall trong tài liệu này đều ghi rõ known-positive, không phải full-corpus recall hoặc accuracy của search.

Nguồn: reports/rag/development_judgments.json; reports/rag/rag_metrics.json; src/rag/evaluation.py.

Tên cột known_hit_at_5/10 được giữ để trace, nhưng ý nghĩa công thức là macro known-positive recall. Binary Hit@k và full Recall@k được giải thích riêng ở phụ lục; không đổi experiment results. MRR V3=0,166667 là mean reciprocal rank trên sáu query.

## 18 Generation và faithfulness

Packet chứa question_intent, aspect, restaurant, evidence và aggregates. Mỗi evidence có ref E1/E2/E3, review_id thật, sentiment/aspects/issues dự đoán, rating và đoạn text giới hạn. Payload generation dùng placeholder ngắn để giảm khả năng model viết sai một ID dài; response cuối map lại ID chính xác.

Nguồn: src/rag_v3/evidence.py::Packet, build_packet, _packet_text, evidence_for_refs.

validate_packet_citations kiểm tra inline refs, danh sách refs, aspect/topic, polarity, số ít/số nhiều, frequency language và mixed evidence. Sau đó tách câu/mệnh đề, yêu cầu citation cho từng assertion và overlap với chính review được dẫn. _clause_supported còn kiểm tra các cue issue, polarity staff attitude và loại numeric claims được sinh.

Nguồn: src/rag_v3/evidence.py::validate_packet_citations, _clause_supported; reports/rag_v3/generation_failure_analysis.json.

Khi có packet hợp lệ nhưng hai lần sinh không qua, extractive_answer chọn evidence đầu, trích tối đa khoảng 180 ký tự và gắn ref. Mode=extractive_fallback hiển thị cho người dùng. Đây là cơ chế bảo toàn evidence, nhưng answer có thể chưa đủ để trả lời câu hỏi “phổ biến nhất”.

Nguồn: src/rag_v3/service.py::answer_question_v3; src/rag_v3/evidence.py::extractive_answer.

Bảng 18. Accepted Qwen3B six-case outcomes

| Outcome | Count | Interpretation |
| --- | --- | --- |
| supported complete | 2 | 1 synthesis + 1 fallback |
| supported incomplete | 1 | fallback không chứng minh phổ biến nhất |
| unsupported accepted | 0 | validator-detected only |
| correct insufficient | 3 | không generation khi evidence thiếu |
| fallback | 2 | subset của supported answers |

Nguồn: reports/rag_v3/generation_metrics.json. Loại: MEASURED.

## 19 Ablation theo bằng chứng

Đây là ablation theo observed progression từ saved artifacts. Không có component-off controls để ước lượng causal effect của packet, validator hay fallback. Evidence packet chấp nhận3 và từ chối3; clause validator ghi5 rejected attempts của Qwen3B; final system giữ useful evidence bằng2 fallbacks. Attempt count không phải số final answers độc lập. Blank/N/A không được thay bằng0.

![Observed retrieval và safety progression](../reports/task2/figures/rag_ablation_final.png)

Hình 5. Observed retrieval và safety progression. Nguồn: reports/task2/figures/rag_ablation_final.png. Nhãn Hit của hình gốc đọc như known-positive recall; không phải causal component-off ablation.

## 20 Benchmark ba LLM

Ba model dùng cùng sáu saved evidence packets, prompt V3, llama.cpp b11429, temperature=0, seed=42, cap 128 output tokens, không rerun retrieval. Qwen2.5 3B và Llama-3.2 3B so với DeepSeek-R1-Distill-Qwen 1,5B. DeepSeek distill có gốc Qwen; gọi là ba nhãn họ sản phẩm không có nghĩa ba kiến trúc base độc lập cùng kích thước.

Final gate giữ cùng 2 complete, 1 incomplete, 3 insufficient ở cả ba; Qwen replay mới fallback 3, Llama 2, DeepSeek 3. DeepSeek không tạo schema parseable trong các ca answerable dưới protocol này; không kết luận model nói chung yếu. Qwen replay mới bị contention và chậm hơn accepted replay, nên không trộn hai lần đo.

Nguồn: reports/task2/llm_comparison.csv; reports/task2/llm_benchmark_provenance.json; reports/task2/LLM_BENCHMARK.md.

Bảng 19. Ba LLM trên fixed packets

| Family | Size MB | Valid schema | Applicable | Fallback | Usage unknown |
| --- | --- | --- | --- | --- | --- |
| Qwen | 2104.932768 | 1 | 3 | 3 | 2 |
| Llama | 2019.377696 | 1 | 3 | 2 | 2 |
| DeepSeek | 1117.320800 | 0 | 3 | 3 | 3 |

Nguồn: reports/task2/llm_comparison.csv. Loại: MEASURED.

Bảng 20. Token và latency theo scope

| Family | Known input | Known output | Active gen ms | Answerable wall ms |
| --- | --- | --- | --- | --- |
| Qwen | 964 | 56 | 112434.980700 | 197793.861933 |
| Llama | 469 | 22 | 61069.005000 | 180586.199733 |
| DeepSeek | N/A | N/A | N/A | 4788.397000 |

Nguồn: reports/task2/llm_comparison.csv. Loại: MEASURED.

![Three family generator smoke](../reports/task2/figures/three_llm_comparison.png)

Hình 6. Three family generator smoke. Nguồn: reports/task2/figures/three_llm_comparison.png. Khác parameter scale và resource contention; không general ranking.

## 21 Tính khả thi

Mean là tổng latency chia số quan sát; p95 là percentile 95, phản ánh phần đuôi chậm. Với numpy/pandas mặc định linear interpolation, p95 có thể nằm giữa hai mẫu. Chỉ sáu query thì percentile rất nhạy; không dùng nó như SLA ổn định cho người dùng thật.

Retrieval latency đo tìm ứng viên; generation latency đo các call hoàn thành; end-to-end gồm retrieval, gate, retries/fallback và overhead. Telemetry cộng usages chỉ của attempts có usage trả về, nên không luôn chứa thời gian timeout. Benchmark còn cột answerable wall time để phản ánh toàn bộ chờ ở các câu có evidence. Mean toàn sáu ca chứa ba refusal nhanh khác mean ba answerable.
Nguồn: src/rag_v3/service.py; scripts/task2_llm_benchmark.py; reports/task2/FEASIBILITY.csv.

Nguồn: src/rag_v3/service.py; scripts/task2_llm_benchmark.py; reports/task2/FEASIBILITY.csv.

Model_size_bytes là kích thước file weights trên đĩa; RSS là bộ nhớ resident của process; VRAM là bộ nhớ GPU. Sampling GPU toàn hệ thống có thể gồm ứng dụng khác và không chứng minh process inference dùng hết lượng đó. Context/KV cache, batch và runtime tạo overhead ngoài weights.

Q4_K_M giảm biểu diễn weights để model chạy trên máy cá nhân, có thể đổi quality. Repository không có đối chứng full precision để tính mất mát do quantization. V1 mất sampler evaluation, chỉ có idle probe riêng; three-family benchmark có sampled RSS nhưng GPU số đo system-wide. Docker nghiệm thu chạy CPU, GPU container NOT VERIFIED dù lệnh yêu cầu gpu layers=99.
Nguồn: reports/proposed_v1/qwen_resource_report.json; reports/task2/llm_comparison.csv; reports/task2/DOCKER_ACCEPTANCE.md.

Nguồn: reports/proposed_v1/qwen_resource_report.json; reports/task2/llm_comparison.csv; reports/task2/DOCKER_ACCEPTANCE.md.

Bảng 21. Feasibility theo từng task

| Component / run | Model MB | Mean ms | p95 ms | Peak RSS bytes |
| --- | --- | --- | --- | --- |
| Rule-based | 0 | 0.023798 | 0.048480 | N/A |
| TF-IDF sentiment | 0.342442 | 0.365186 | 0.417170 | N/A |
| Aspect TF-IDF | N/A | N/A | N/A | N/A |
| Qwen 1.5B | 1117.320736 | 1580.140133 | N/A | 1502134272 |
| Qwen 3B | 2104.932768 | 1498.382233 | N/A | 2473472000 |
| Qwen research replay | 2104.932768 | 112434.980700 | 112434.980700 | 1935290368 |
| Llama research replay | 2019.377696 | 61069.005000 | 61069.005000 | 2820562944 |
| DeepSeek research replay | 1117.320800 | 4788.397000 | 4822.688100 | 1499504640 |
| MiniLM dense retrieval | 235.052644 | 16.519117 | 21.181625 | N/A |
| RAG V3 end-to-end | N/A | 870.369067 | 1836.472750 | N/A |

Nguồn: reports/task2/FEASIBILITY.csv. Loại: MEASURED.

![Latency và kích thước artifact](../reports/task2/figures/latency_model_size.png)

Hình 7. Latency và kích thước artifact. Nguồn: reports/task2/figures/latency_model_size.png. Các task/run khác nhau; DeepSeek dùng answerable wall khi active generation không có.

## 22 Kiến trúc hệ thống

Hình tổng thể tách research offline khỏi demo. Classifier cổ điển tạo nhãn dự đoán; retrieval tìm bằng chứng; LLM diễn đạt; validator/fallback quyết định đầu ra được chấp nhận. Vì thế “LLM everything” không phù hợp evidence hiện tại: TF-IDF phân loại tốt hơn V1 và nhỏ/nhanh hơn trong các đo đã có, còn LLM có khả năng viết câu.

Nguồn: reports/task2/figures/final_architecture.png; app/app.py; docker-compose.yml.

![Kiến trúc logic research và demo](../reports/task2/figures/final_architecture.png)

Hình 8. Kiến trúc logic research và demo. Nguồn: reports/task2/figures/final_architecture.png. Deployment hops cần đọc chương Docker; UI không gọi V3 qua FastAPI.

## 23 Docker và microservices

Default services: pipeline chạy CLI help một lần; qwen chạy llama-server; rag-backend chạy FastAPI; streamlit chạy giao diện. prefect-server và scheduler nằm trong profile orchestration, không bật mặc định và không bắt buộc cho acceptance hiện tại.

Luồng đúng theo source: Browser → Streamlit :8501 → module RAG V3 trong container Streamlit → Qwen :8193; module đọc Chroma/BM25 qua data mount và ghi state SQLite. rag-backend :8000 là service song song có API legacy. Qwen local launcher dùng :8194; QWEN_BASE_URL=http://qwen:8193 trong Compose override URL kết nối.

Nguồn: app/app.py; app/api.py; src/llm/gateway.py; docker-compose.yml.

Traceback của pipeline là ModuleNotFoundError: No module named 'psutil'. src.cli import rag_v3.cli → llm.gateway → proposed_v1.runtime, nơi import psutil. Image pipeline cài requirements.txt, trong khi psutil đã có ở requirements-demo.txt; sửa file demo sẽ không sửa dependency của pipeline.

Nguồn: requirements.txt; Dockerfile; src/proposed_v1/runtime.py; reports/task2/DOCKER_ACCEPTANCE.md.

Pipeline default command là python -m src.cli --help. Nó là one-shot: in usage rồi kết thúc. Exited (0) xác nhận hành vi này thành công; không cần giữ process bằng sleep để gọi healthy. Exit non-zero trước action mới là startup failure cần điều tra.

Nguồn: Dockerfile; docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md.

Bảng 22. Service boundary thực tế

| Service | Role | Port / state | Scope |
| --- | --- | --- | --- |
| pipeline | CLI one-shot | exit0 | --help, không ingestion |
| qwen | llama-server 3B | 8193 healthy | CPU accepted; GPU chưa verified |
| rag-backend | FastAPI legacy | 8000 Up HTTP200 | Không phải V3 Analyst API |
| streamlit | UI + V3 modules | 8501 Up HTTP200 | Direct V3→Qwen |
| prefect-server/scheduler | orchestration profile | optional 4200 | Không bật mặc định |

Nguồn: docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md. Loại: CONFIGURED + MEASURED acceptance.

## 24 CI CD

CI tự động kiểm tra source mới để phát hiện lỗi trước khi tích hợp. CD ở project là build và publish application image lên GitHub Container Registry. Workflow không khai báo remote deployment environment, database migration hay rollout production; publish thành công không có nghĩa người dùng ngoài Internet đã truy cập ứng dụng.

Nguồn: .github/workflows/ci.yml; .github/workflows/release.yml; reports/task2/DOCKER_ACCEPTANCE.md.

CI chạy khi push main/develop, pull request tới main và workflow_dispatch. Job quality-and-tests dùng ubuntu-latest, Python 3.12, requirements-ci.txt, Ruff, compileall src app scripts, pytest xuất JUnit, rồi import app.app và app.api. Upload JUnit dùng if:always để có report cả khi test lỗi.

Nguồn: .github/workflows/ci.yml; requirements-ci.txt.

Release trigger v* tag hoặc workflow_dispatch với version. Step validate kiểm regex vMAJOR.MINOR.PATCH có thể có prerelease; setup-buildx tạo builder; login-action đăng nhập ghcr.io bằng github.actor/GITHUB_TOKEN; metadata-action sinh tags; build-push-action build Dockerfile.rag và push:true.

Nguồn: .github/workflows/release.yml.

GHCR là registry lưu image layers và manifests; URL ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 chỉ một image reference. Tag thuận tiện nhưng có thể thay đổi; digest xác định nội dung manifest. Release hiện xác minh index digest sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a, có linux/amd64 manifest.

CI run 39739640437 và release run 39742439011 đều success tại commit 4229a8b3998392c97f4b7a8c9e3795830285dbce. Đây là cập nhật mới hơn CICD_EVIDENCE.md còn nhắc v1.0.0. Tài liệu lưu kiểm tra read-only ngày 22/10/2026; không sửa workflow hoặc phát hành image mới.
Nguồn: public GitHub Actions run URLs trong Evidence Map; docker buildx imagetools inspect v1.0.1 tại audit.

Nguồn: public GitHub Actions run URLs trong Evidence Map; docker buildx imagetools inspect v1.0.1 tại audit.

Public API và GHCR read-only audit22/10/2026 xác nhận post-fix v1.0.1, mới hơn report CICD_EVIDENCE trong repo. CI/release tại4229a8b không bao phủ các tài liệu đang tạo. Image digest đầy đủ nằm ở Evidence Map. Các tag/alias theo workflow, không giả định deployment.

## 25 Reproducibility

Dataset revision và raw hashes xác định nguồn; preparation hash xác định dữ liệu chuẩn hóa; split hash xác định membership. Runner chọn cấu hình từ validation, lưu model/prompt/protocol hashes, predictions và metrics. MLflow run_id cho phép nối candidate với evidence. DVC khai báo quan hệ dependencies và outputs, không đảm bảo một lệnh reproduce sẽ nhẹ.

Historical experiments đã hoàn tất nên không chạy dvc repro toàn bộ chỉ để xem demo. Có checkpoint/guard tránh vô tình đánh giá test lần hai, nhưng nghiên cứu V2 vẫn công khai test đã được nhìn. Reproducibility nghĩa có thể truy vết và thiết lập lại điều kiện, không có nghĩa mọi hệ điều hành sẽ tạo timing hoặc bit-identical floating point giống nhau.
Nguồn: dvc.yaml; dvc.lock; params.yaml; src/baselines/runner.py; src/proposed_v1/runner.py.

Nguồn: dvc.yaml; dvc.lock; params.yaml; src/baselines/runner.py; src/proposed_v1/runner.py.

Dataset revision6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4; split hash860387be19c64220f91cc2b5e764aa3c99aa18daba9c776fde38e05da30a5ff9; seed42; model/prompt hashes trong provenance/selection; DVC lock và requirements pins trong repo. Last recorded tests288 passed1 warning, Ruff/compileall PASS. Tài liệu tái tính từ saved outputs và không retrain/retest model.

## 26 Luồng demo cuối

Browser gửi tương tác tới Streamlit. analyst_page tạo RetrievalRequest từ text/filter và chọn gateway 3B. RoutedRetriever kiểm manifest rồi chọn policy; packet gate lọc evidence; gateway gửi chat JSON qua HTTP llama.cpp; validator kiểm từng clause; response cuối mang mode/citations; record ghi telemetry.

Nghiệm thu Hanuri với câu “Nhân viên phục vụ có vấn đề gì không?” trả extractive_fallback có citation thật và event LLMOps. Log đã lưu event 403 với retrieval khoảng 5.027 ms, LLM khoảng 41.969 ms, end-to-end khoảng 47.415 ms trên container CPU. Đây là một request runtime khác accepted GPU/local replay, không dùng để thay các metric benchmark đã đóng băng.
Nguồn: app/app.py::analyst_page; reports/task2/DOCKER_ACCEPTANCE.md.

Nguồn: app/app.py::analyst_page; reports/task2/DOCKER_ACCEPTANCE.md.

## 27 Giới hạn

Giới hạn dữ liệu: label aspect-level có xung đột text-only; neutral ít; Foody không có gold labels; tên nhà hàng chưa là ID chính thức; sampling review có thiên lệch. Giới hạn model: probability chưa calibrated Foody, issue heuristic, zero-support aspects và một số lựa chọn parameter chưa có controlled search.

Giới hạn RAG: sáu query với relevance chưa đầy đủ, truncation embedding dài, rule support không phải human entailment, latency khác run/hardware và generator fallback nhiều. Ablation là observed progression, không có packet-off/validator-off/fallback-off controls. GPU Docker chưa được xác minh; không train LLM from scratch; CD không phải remote production deployment.

Nguồn: reports/task2/TRAINING_SCOPE.md; reports/task2/LLM_BENCHMARK.md; reports/task2/CHUNKING_DECISION.md.

## 28 Kết luận

Kết quả ủng hộ kiến trúc chia vai trò: TF-IDF LR cho classification, model aspect độc lập cho chủ đề, Qwen cho diễn đạt evidence và deterministic gates cho khả năng kiểm chứng. V1/V2 không được quảng bá là vượt baseline mạnh; RAG V3 được chấp nhận trong tập ca local giới hạn. Đóng góp Task2 là chuỗi experiment có failure analysis, accounting tài nguyên, source traceability và runtime/image-delivery evidence. Bước tiếp theo nên ưu tiên relevance set và human support evaluation độc lập trước khi đổi kiến trúc.

## 29 Checklist Task 2

Bảng 23. Task2 teacher checklist

| Item | Status | Evidence / limit |
| --- | --- | --- |
| 1. Data source table | DONE | dataset_sources.csv |
| 2. Cleaning/labeling | DONE | CLEANING_FLOW.md |
| 3. Train/Val/Test | DONE | DATASET_SUMMARY.md |
| 4. Leakage checks | DONE | DATASET_SUMMARY.md |
| 5. Imbalance | DONE | class_distribution.csv |
| 6. Imbalance handling | DONE | imbalance_comparison.csv |
| 7. Baseline 1 | DONE | classical_model_comparison.csv |
| 8. Baseline 2 | DONE | classical_model_comparison.csv |
| 9. 3-seed stability | DONE | baseline_three_seed.csv |
| 10. Paper vs Group | DONE | PAPER_VS_GROUP.md |
| 11. Gap Analysis | DONE | GAP_ANALYSIS.md |
| 12. Proposed V1 | DONE | ../proposed_v1/qwen_test_metrics.json |
| 13. Failure analysis | DONE | failure_counts.csv |
| 14. V2/V3 | DONE | ../rag_v3/generation_metrics.json |
| 15. Ablation | DONE | RAG_ABLATION_FINAL.md`, `figures/rag_ablation_final.png` (observed contributions; no component-off control) |
| 16. Latency/model size | DONE | FEASIBILITY.csv |
| 17. RAG chunking/token accounting | DONE | rag_token_statistics.json |
| 18. Embedding/vector DB | DONE | embedding_workload.csv |
| 19. Retrieval metrics | DONE | RAG_ABLATION.csv |
| 20. Generation/faithfulness | DONE | LLM_BENCHMARK.md |
| 21. Docker/microservices | DONE | DOCKER_ACCEPTANCE.md` (serving path and pipeline startup accepted) |
| 22. GitHub Actions CI/CD | DONE | CICD_EVIDENCE.md` (CI, release job and GHCR manifest verified) |
| 23. Reproducibility | DONE | baseline_three_seed.csv |
| 24. Slide-ready figures | DONE | figures/ |

Nguồn: reports/task2/TASK2_SELF_ASSESSMENT.md. Loại: AUDITED STATUS.

24/24 DONE theo tiêu chí evidence của checklist. Caveats giữ nguyên: không full LLM training from scratch, không production remote deployment, GPU Docker chưa xác minh, benchmark sáu ca và observational ablation không chứng minh general superiority.

## 30 Phụ lục

### A Lệnh vận hành

Các lệnh dưới đây là hướng dẫn, không được thực thi bởi script tài liệu. Demo dùng artifact local đã có; clone từ GitHub một mình không chứa weights/data/index. Không chạy train, download hoặc dvc repro toàn pipeline để chỉ mở demo.

```powershell
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
```

CI/release flow: review diff → commit/push lên branch phù hợp → xác minh CI tại đúng SHA → tạo một tag phiên bản mới chưa tồn tại → push tag → xem publish run và GHCR digest. v1.0.1 đã tồn tại, không tạo lại hoặc force-push tag. Full demo dependency provisioning có nhiều requirements và local runtime artifacts; hướng dẫn ưu tiên .venv đã nghiệm thu thay vì hứa một pip install tải đủ dữ liệu riêng.

### B Repo map

Bảng 24. Module groups

| Group | Role |
| --- | --- |
| src/food + baselines + proposed* | Research frozen experiments |
| src/foody | Offline inference và marts |
| src/rag + rag_v2 + rag_v3 | Shared retrieval và active V3 safety |
| app + config + prompts | UI/API và serving selection |
| scripts + tests | Research/verify/launch và tests |
| .github + Dockerfiles | CI và image delivery |

Nguồn: source inventory. Loại: SOURCE AUDIT.

### C Config và artifact identities

Active sentiment=models/tfidf_logreg.joblib; aspect=models/aspect_tfidf.joblib; Qwen3B revisioncc1e68eea5f05f88f41a6de1fc73110178f23715; embedding revisionfaf4aa4225822f3bc6376869cb1164e8e3feedd0; prompt rag_v3:81e19ef10f78. Nguồn: config/demo.yaml; qwen_v3_3b.yaml; reports/rag/embedding_selection.json.

### D Công thức

### F01 Imbalance ratio

Công thức F01: IR = max(n_c) / min(n_c)

Input và thế số: 3714 / 294. Kết quả: 12.632653.

Diễn giải: Lớp đông gấp 12,63 lần lớp ít. Loại: DERIVED.

### F02 Balanced class weights

Công thức F02: w_c = N / (K × n_c)

Input và thế số: 4140/(3×1307); 4140/(3×208); 4140/(3×2625). Kết quả: 1.055853099; 6.634615385; 0.525714286.

Diễn giải: Train-only; không đổi số mẫu. Loại: DERIVED.

### F03 Term frequency

Công thức F03: TF_intro = count / length; TF_project = 1 + ln(count) nếu count>0

Input và thế số: EXAMPLE count=3,length=10: 3/10; 1+ln(3). Kết quả: 0.3; 2.098612289.

Diễn giải: Ví dụ minh họa, không phải số liệu project. Loại: THEORY/EXAMPLE.

### F04 Smoothed IDF

Công thức F04: IDF = ln((1+N)/(1+df)) + 1

Input và thế số: EXAMPLE N=100,df=10: ln(101/11)+1. Kết quả: 3.217225.

Diễn giải: Vocabulary/IDF học train; minh họa. Loại: THEORY/EXAMPLE.

### F05 TF IDF và L2

Công thức F05: u_t = TF_t × IDF_t; x = u / sqrt(Σ u_t²)

Input và thế số: EXAMPLE u=[3,4] → norm=5. Kết quả: [0.6,0.8].

Diễn giải: Minh họa chuẩn hóa vector, không phải review embedding. Loại: THEORY/EXAMPLE.

### F06 Logistic sigmoid

Công thức F06: z = wᵀx+b; σ(z)=1/(1+exp(−z))

Input và thế số: EXAMPLE z=0. Kết quả: 0.500000.

Diễn giải: Nhị phân OVR aspect, không công thức 3-class sentiment. Loại: THEORY/EXAMPLE.

### F07 Multinomial softmax

Công thức F07: p_c = exp(z_c) / Σ_j exp(z_j)

Input và thế số: EXAMPLE scores=[0,0,0]. Kết quả: [1/3,1/3,1/3].

Diễn giải: Xác suất ba lớp cộng thành1. Loại: THEORY/EXAMPLE.

### F08 Accuracy thật từ confusion

Công thức F08: accuracy = Σ diagonal / N

Input và thế số: (228+19+471)/887. Kết quả: 0.809470.

Diễn giải: Tính lại prediction đã lưu, không test inference mới. Loại: DERIVED.

### F09 Neutral precision

Công thức F09: P = TP/(TP+FP)

Input và thế số: 19/(9+19+21). Kết quả: 0.387755.

Diễn giải: 49 predicted-neutral, 19 đúng. Loại: DERIVED.

### F10 Neutral recall

Công thức F10: R = TP/(TP+FN)

Input và thế số: 19/(10+19+14). Kết quả: 0.441860.

Diễn giải: Tìm được19 trong43 gold-neutral. Loại: DERIVED.

### F11 Neutral F1

Công thức F11: F1 = 2PR/(P+R) = 2TP/(2TP+FP+FN)

Input và thế số: 38/(38+30+24). Kết quả: 0.413043.

Diễn giải: Trade-off precision/recall. Loại: DERIVED.

### F12 Macro F1

Công thức F12: macro-F1 = (Σ_c F1_c)/K

Input và thế số: (0.7728813559322034+0.4130434782608696+0.8626373626373627)/3. Kết quả: 0.682854.

Diễn giải: Mỗi lớp cùng trọng số. Loại: DERIVED.

### F13 Weighted F1

Công thức F13: weighted-F1 = Σ support_c×F1_c / N

Input và thế số: (284×F1_negative+43×F1_neutral+560×F1_positive)/887. Kết quả: 0.812104.

Diễn giải: Lớp đông ảnh hưởng lớn. Loại: DERIVED.

### F14 Micro F1 và exact match

Công thức F14: micro-F1=2ΣTP/(2ΣTP+ΣFP+ΣFN); exact=mean(whole set equal)

Input và thế số: EXAMPLE gold={food,service}, pred={food}: TP1 FP0 FN1. Kết quả: micro-F1=2/3; exact=0.

Diễn giải: Ví dụ một mẫu multi-label. Loại: THEORY/EXAMPLE.

### F15 Stride

Công thức F15: S = C − O

Input và thế số: 256−32. Kết quả: 224.

Diễn giải: Bước dịch cửa sổ minh họa. Loại: THEORY/EXAMPLE.

### F16 Số chunk

Công thức F16: N=max(1,ceil((T−C)/(C−O))+1)

Input và thế số: max(1,ceil((900−256)/224)+1). Kết quả: 4.

Diễn giải: Ví dụ minh họa, không rebuild index. Loại: THEORY/EXAMPLE.

### F17 Corpus token average

Công thức F17: T_total=Σ_i T_i; T_mean=T_total/N

Input và thế số: MiniLM 3750416/32457; Qwen4105360/32457. Kết quả: 115.550297316; 126.486120097.

Diễn giải: Hai tokenizer, không cộng totals. Loại: DERIVED.

### F18 Raw vector payload

Công thức F18: B=N×d×bytes_per_scalar; MB=B/10⁶; MiB=B/2²⁰

Input và thế số: 32457×384×4. Kết quả: 49853952 bytes; 49.853952 MB; 47.544434 MiB.

Diễn giải: Chỉ payload float32, không phải total disk/RSS. Loại: DERIVED.

### F19 Binary Hit at k

Công thức F19: Hit@k = mean_q I(top-k intersects relevant)

Input và thế số: EXAMPLE [1,0,1]: 2/3. Kết quả: 0.666667.

Diễn giải: Không dùng formula này để gọi giá trị recall cũ là Hit. Loại: THEORY/EXAMPLE.

### F20 Known-positive recall at k

Công thức F20: KPRecall@k = mean_q |top-k∩KP_q|/|KP_q|

Input và thế số: EXAMPLE hai positives, một vào top5: 1/2. Kết quả: 0.500000.

Diễn giải: Code project dùng đây cho cột known_hit. Loại: THEORY/EXAMPLE.

### F21 Mean và sample standard deviation

Công thức F21: mean=Σx/n; s=sqrt(Σ(x−mean)²/(n−1))

Input và thế số: Ba test macro-F1=0.6828540656101453. Kết quả: mean=0.6828540656101453; sample SD=0.

Diễn giải: Không đo split uncertainty. Loại: DERIVED.

### F22 Improvement signals

Công thức F22: Δ = metric_proposed − metric_reference

Input và thế số: 0.6217892057−0.4312787686; −0.6828540656; neutral0.2577777778−0.4130434783. Kết quả: 0.190510437; -0.061064860; -0.155265700.

Diễn giải: Chỉ positive so với rule. Loại: DERIVED.

### F23 Embedding throughput và simulation

Công thức F23: throughput=N/seconds; estimated time=chunks/throughput

Input và thế số: 32457/1054.6336726; 49063/30.7756151195. Kết quả: 30.775615119 docs/s; 1594.216714 s.

Diễn giải: Thời gian alternate policy là estimate. Loại: DERIVED.

### F24 RRF

Công thức F24: RRF(d)=Σ_r 1/(k+rank_r(d))

Input và thế số: EXAMPLE A:1/61+1/64; B:2/62. Kết quả: A=0.032018443; B=0.032258065.

Diễn giải: B nhỉnh hơn trong ví dụ. Loại: THEORY/EXAMPLE.

### F25 BM25

Công thức F25: score(D,Q)=Σ IDF(q)×f(q,D)(k1+1)/(f(q,D)+k1(1−b+b|D|/avgdl))

Input và thế số: THEORY f=1,k1=1.2,b=.75,|D|=avgdl: multiplier=2.2/2.2. Kết quả: 1.

Diễn giải: SQLite trả negative rank; code đảo dấu; IDF theo FTS5. Loại: THEORY/EXAMPLE.

### F26 Mean reciprocal rank

Công thức F26: MRR=(1/Q)Σ_q 1/rank_q; missing→0

Input và thế số: EXAMPLE (1+1/4+0)/3. Kết quả: 0.416667.

Diễn giải: Chỉ relevant đầu tiên. Loại: THEORY/EXAMPLE.

### F27 Mean latency

Công thức F27: L_mean=Σ latency_i/n

Input và thế số: EXAMPLE [100,200,300] ms. Kết quả: 200.

Diễn giải: Phải thống nhất scope retrieval/generation/end-to-end. Loại: THEORY/EXAMPLE.

### F28 Percentile p95

Công thức F28: h=(n−1)×0.95; interpolate sorted x at h

Input và thế số: EXAMPLE [100,200,300]: h=1.9, 200+.9×100. Kết quả: 290.

Diễn giải: Linear interpolation; minh họa không là project latency. Loại: THEORY/EXAMPLE.

### F29 Review vượt 128 tokens

Công thức F29: rate = n_exceed / n_docs ×100

Input và thế số: 11235/32457×100. Kết quả: 34.615029.

Diễn giải: Material embedding truncation limitation. Loại: DERIVED.

### F30 V1 test token usage

Công thức F30: total=input+output; mean=total/N

Input và thế số: 249190+6210=255400; 255400/887. Kết quả: 287.936866.

Diễn giải: Không cộng corpus tokenizer totals; gồm protocol request. Loại: DERIVED.

### E Parameter selection

Bảng 25. Validation selected và fixed choices

| Parameter | Selected | Evidence/limit |
| --- | --- | --- |
| Sentiment ngram_range | (1,2) | (1,1), C=1: val macro-F1 0,648722; (1,2), C=1: 0,700294; (1,2), C=2: 0,709242 |
| Sentiment C | 2 | C=1 và 2 với bigram: 0,700294 và 0,709242 |
| class_weight sentiment | balanced | None → neutral val F1 0,170213; balanced → 0,471910 |
| Seed | 42 | So sánh 42,123,2026 cho cùng test macro-F1 0,682854 |
| Aspect C | 2 | C=0,5/2 × threshold=0,3/0,5/0,7; bảng sáu trial |
| Aspect threshold | 0.5 | 0,3/0,5/0,7 tại C=2: micro-F1 0,761201/0,821752/0,764747 |
| Chunk policy | one review one document | Mô phỏng 128/0,128/32,256/0,256/32,512/0,512/64; không đánh giá index thay thế |
| Embedding model | multilingual MiniLM L12 v2 | Pool 612: Potion known recall@10 0,166667; MiniLM 0,333333 |
| Embedding dimensions | 384 | Potion có 256 nhưng là model khác |
| LLM demo | Qwen2.5 3B Q4_K_M | Accepted 1,5B fallback=3; 3B fallback=2 trên sáu ca |

Nguồn: source config/candidate CSV. Loại: CONFIGURED + MEASURED.

Các giá trị cố định như max_features, min_df, RRF60, top-k5, packet3, context2048, temperature0, quantization và ports không có controlled search riêng. Full32 decision cards và ảnh hưởng tăng/giảm ở Master Guide/notebook.

### F Evidence index

Bảng 26. Evidence Map 1

| Claim | Value | Type / verified | Evidence |
| --- | --- | --- | --- |
| Research source rows | 76785 | MEASURED / Có | reports/food_dataset_report.json |
| Vietnamese restaurant rows | 5869 | MEASURED / Có | reports/food_dataset_report.json |
| Review IDs | 1530 | MEASURED / Có | reports/food_dataset_report.json |
| Normalized texts | 5316 | MEASURED / Có | reports/food_dataset_report.json |
| Sentiment distribution | {"positive": 3714, "negative": 1861, "neutral": 294} | MEASURED / Có | reports/task2/class_distribution.csv |
| Imbalance ratio | 12.632653 | DERIVED / Có | reports/task2/class_distribution.csv |
| Split rows | {"train": 4140, "test": 887, "validation": 842} | MEASURED / Có | data/food/splits/metadata.json |
| Leakage checks | {"review_ids_spanning_splits": 0, "normalized_texts_spanning_splits": 0} | MEASURED / Có | data/food/splits/metadata.json |

Nguồn: source paths trong từng dòng. Loại: MIXED.

Bảng 27. Evidence Map 2

| Claim | Value | Type / verified | Evidence |
| --- | --- | --- | --- |
| Split SHA256 | 860387be19c64220f91cc2b5e764aa3c99aa18daba9c776fde38e05da30a5ff9 | MEASURED / Có | data/food/splits/metadata.json |
| Foody raw rows | 33946 | MEASURED / Có | reports/foody_intelligence/cleaning.json |
| Foody valid rows | 33938 | MEASURED / Có | reports/foody_intelligence/cleaning.json |
| Foody inference observations | 31694 | MEASURED / Có | reports/foody_intelligence/cleaning.json |
| Foody distinct valid reviews | 32457 | MEASURED / Có | reports/foody_intelligence/cleaning.json |
| Foody restaurants | 2110 | MEASURED / Có | reports/foody_intelligence/cleaning.json |
| Rule test macro-F1 | 0.431279 | MEASURED / Có | reports/baselines/rule_based_test_metrics.json |
| TF-IDF test macro-F1 | 0.682854 | MEASURED / Có | reports/baselines/tfidf_test_metrics.json |

Nguồn: source paths trong từng dòng. Loại: MIXED.

Bảng 28. Evidence Map 3

| Claim | Value | Type / verified | Evidence |
| --- | --- | --- | --- |
| Qwen V1 test macro-F1 | 0.621789 | MEASURED / Có | reports/proposed_v1/qwen_test_metrics.json |
| Qwen V2-A test macro-F1 | 0.614487 | MEASURED / Có | reports/proposed_v2/test_metrics.json |
| Three-seed test macro-F1 | 0.682854 ± 0 (sample SD) | DERIVED / Có | reports/task2/baseline_three_seed.csv |
| Aspect micro/macro F1 | 0.832276657 / 0.633628001 | MEASURED / Có | reports/aspect_classifier/test_metrics.json |
| RAG documents/vectors/BM25 | 32457 / 32457 / 32457 | MEASURED / Có | reports/task2/DOCKER_ACCEPTANCE.md |
| MiniLM corpus tokens | 3750416 | MEASURED / Có | reports/task2/rag_token_statistics.json |
| Qwen corpus tokens | 4105360 | MEASURED / Có | reports/task2/rag_token_statistics.json |
| Embedding dimensions | 384 | CONFIGURED/EXTERNAL / Có | src/rag/embeddings.py |

Nguồn: source paths trong từng dòng. Loại: MIXED.

Bảng 29. Evidence Map 4

| Claim | Value | Type / verified | Evidence |
| --- | --- | --- | --- |
| Embedding seconds | 1054.633673 | MEASURED / Có | data/foody/vector_store/index_manifest.json |
| Raw vector bytes | 49853952 | DERIVED / Có | src/rag/embeddings.py; Chroma manifest |
| Dense/V2/V3 MRR | 0.018518519 / 0.055555556 / 0.166666667 | MEASURED / Có | reports/rag_v3/retrieval_policies.csv |
| Historical Hit@5/10 naming | Actual formula = macro known-positive recall | SOURCE AUDIT / Có | src/rag/evaluation.py |
| V3 accepted generator | 2 complete / 1 incomplete / 0 unsupported / 3 insufficient / 2 fallback | MEASURED / Có | reports/rag_v3/generation_metrics.json |
| Three-family benchmark | 6 cases per model | MEASURED / Có | reports/task2/llm_comparison.csv |
| Latency and model sizes | Tách từng task/run; xem bảng feasibility | MEASURED / Có | reports/task2/FEASIBILITY.csv |
| Docker | pipeline exit0; qwen healthy; backend/UI HTTP200 | MEASURED / Có | reports/task2/DOCKER_ACCEPTANCE.md |

Nguồn: source paths trong từng dòng. Loại: MIXED.

Bảng 30. Evidence Map 5

| Claim | Value | Type / verified | Evidence |
| --- | --- | --- | --- |
| Tests | 288 passed / 1 warning | MEASURED / Có | reports/task2/REVIEW2_STATUS_SUMMARY_VI.md |
| CI | 39739640437 success at 4229a8b | MEASURED / Có | https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39739640437 |
| CD release | 39742439011 success v1.0.1 | MEASURED / Có | https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39742439011 |
| GHCR manifest | sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a | MEASURED / Có | ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 |

Nguồn: source paths trong từng dòng. Loại: MIXED.

### G Câu hỏi bảo vệ

### Câu hỏi 1 Project giải quyết vấn đề gì?

Trả lời ngắn: Người quản lý nhà hàng cần biết khách đang khen hoặc phàn nàn điều gì, tại chi nhánh nào và trong khoảng thời gian nào.

Giải thích sâu: Có hai luồng độc lập. VN-MSASar cung cấp nhãn nghiên cứu để huấn luyện và đánh giá classifier; Foody là dữ liệu thực tế để suy luận, dashboard và RAG. Kết quả tốt trên VN-MSASar không tự biến thành accuracy trên Foody. Sản phẩm là demo chạy local đã nghiệm thu, chưa có bằng chứng triển khai production từ xa.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Không biến demo local thành tuyên bố production toàn diện.

Evidence và file/code để mở: README.md; src/foody/pipeline.py; app/app.py; reports/task2/TRAINING_SCOPE.md.

### Câu hỏi 2 5.869 mẫu có phải 5.869 review độc lập không?

Trả lời ngắn: Nguồn public là phamluan/vn_msa_sar_v3 trên Hugging Face, revision 6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4, license CC BY 4.0 theo provenance.

Giải thích sâu: Một dòng biểu diễn câu và aspect được gán nhãn, không nhất thiết là một review độc lập. Có 1.530 review_id và 5.316 câu chuẩn hóa riêng biệt. Schema nguồn gồm review_id, source, place_type, language, sentence, aspect, sentiment, sarcasm. Adapter đổi sentence thành text, giữ original_text và original_sentiment, lưu metadata provenance. research source=foody không có nghĩa là cùng export Foody first-party dùng cho demo.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Phân biệt row, review ID, normalized text và document.

Evidence và file/code để mở: reports/food_dataset_report.json; src/food/adapters.py; data/food/source/vn_msasar_v3/provenance.json.

### Câu hỏi 3 Dataset lấy ở đâu và version nào?

Trả lời ngắn: Nguồn public là phamluan/vn_msa_sar_v3 trên Hugging Face, revision 6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4, license CC BY 4.0 theo provenance.

Giải thích sâu: Một dòng biểu diễn câu và aspect được gán nhãn, không nhất thiết là một review độc lập. Có 1.530 review_id và 5.316 câu chuẩn hóa riêng biệt. Schema nguồn gồm review_id, source, place_type, language, sentence, aspect, sentiment, sarcasm. Adapter đổi sentence thành text, giữ original_text và original_sentiment, lưu metadata provenance. research source=foody không có nghĩa là cùng export Foody first-party dùng cho demo.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Revision/hash pin quan trọng hơn tên dataset giống nhau.

Evidence và file/code để mở: reports/food_dataset_report.json; src/food/adapters.py; data/food/source/vn_msasar_v3/provenance.json.

### Câu hỏi 4 Nhãn sentiment được tạo thế nào?

Trả lời ngắn: Thang sentiment nguồn là số nguyên từ −3 đến +3.

Giải thích sâu: THEORY: negative biểu đạt không hài lòng; positive biểu đạt hài lòng; neutral là trung tính theo nhãn nguồn. EXAMPLE: −2 và −1 cùng trở thành negative, +1 và +3 cùng positive. PROJECT RESULT: original_sentiment được giữ để truy vết; ba nhãn được dùng nhất quán trong metrics. Gộp nhãn làm bài toán đơn giản hơn nhưng mất thông tin cường độ và vẫn không giải quyết câu có cảm xúc khác nhau theo aspect.

Công thức: sign(label). Điểm dễ nhầm: Không dùng rating để tạo research target.

Evidence và file/code để mở: src/food/adapters.py::ordinal và LABEL_MAPPING; reports/food_label_mapping.json.

### Câu hỏi 5 Vì sao cần validation riêng?

Trả lời ngắn: Train dùng để fit vocabulary, IDF và trọng số classifier.

Giải thích sâu: assign_splits không chia từng dòng độc lập: leakage_groups dùng thành phần liên thông nối các dòng chung review_id hoặc text chuẩn hóa. Vì thế một review hoặc câu giống hệt không đi vào nhiều split. Thuật toán tìm 64 phương án GroupShuffleSplit theo seed 42 rồi chọn phương án gần tỷ lệ và phân bố lớp mong muốn; đây là tìm split bằng nhãn, không phải chọn theo điểm dự đoán test. Tỷ lệ thực không đúng tuyệt đối 70/15/15 do ràng buộc nhóm.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Không chọn prompt dựa trên test.

Evidence và file/code để mở: src/food/split.py::leakage_groups, assign_splits, load_splits; data/food/splits/metadata.json.

### Câu hỏi 6 Group split ngăn leakage như thế nào?

Trả lời ngắn: Train dùng để fit vocabulary, IDF và trọng số classifier.

Giải thích sâu: assign_splits không chia từng dòng độc lập: leakage_groups dùng thành phần liên thông nối các dòng chung review_id hoặc text chuẩn hóa. Vì thế một review hoặc câu giống hệt không đi vào nhiều split. Thuật toán tìm 64 phương án GroupShuffleSplit theo seed 42 rồi chọn phương án gần tỷ lệ và phân bố lớp mong muốn; đây là tìm split bằng nhãn, không phải chọn theo điểm dự đoán test. Tỷ lệ thực không đúng tuyệt đối 70/15/15 do ràng buộc nhóm.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Zero exact overlap không đảm bảo zero fuzzy duplicate.

Evidence và file/code để mở: src/food/split.py::leakage_groups, assign_splits, load_splits; data/food/splits/metadata.json.

### Câu hỏi 7 Imbalance ratio được tính ra sao?

Trả lời ngắn: Positive chiếm 3.714 dòng, negative 1.861 và neutral 294.

Giải thích sâu: DERIVED: imbalance ratio = 3.714 / 294 = 12,632653. Neutral chiếm 294 / 5.869 × 100 = 5,009371%. Tỷ lệ này mô tả toàn bộ tập nghiên cứu, không phải weight tính khi train. Class weighting không thay đổi biểu đồ số dòng nên không có một phân bố sample sau cân bằng mới.

Công thức: F01. Điểm dễ nhầm: Dùng majority/minority cùng một population.

Evidence và file/code để mở: reports/task2/class_distribution.csv; reports/food_dataset_report.json.

### Câu hỏi 8 Vì sao neutral có weight lớn nhất?

Trả lời ngắn: Balanced weight tăng chi phí của lỗi ở lớp ít ví dụ.

Giải thích sâu: Validation cho thấy neutral recall tăng từ 0,093023 lên 0,488372 và neutral F1 tăng từ 0,170213 lên 0,471910 khi dùng balanced. Precision neutral giảm từ 1 xuống 0,456522: mô hình tìm thêm neutral nhưng cũng tạo false positives. Đây là trade-off có đo đạc, không phải lời khẳng định mọi lớp đều tốt hơn.

Công thức: F02. Điểm dễ nhầm: Weight lấy train counts, không lấy toàn bộ dataset.

Evidence và file/code để mở: src/baselines/tfidf_logreg.py; reports/task2/imbalance_comparison.csv.

### Câu hỏi 9 Class weight có tạo thêm mẫu không?

Trả lời ngắn: Balanced weight tăng chi phí của lỗi ở lớp ít ví dụ.

Giải thích sâu: Validation cho thấy neutral recall tăng từ 0,093023 lên 0,488372 và neutral F1 tăng từ 0,170213 lên 0,471910 khi dùng balanced. Precision neutral giảm từ 1 xuống 0,456522: mô hình tìm thêm neutral nhưng cũng tạo false positives. Đây là trade-off có đo đạc, không phải lời khẳng định mọi lớp đều tốt hơn.

Công thức: F02. Điểm dễ nhầm: Số rows trước/sau không đổi.

Evidence và file/code để mở: src/baselines/tfidf_logreg.py; reports/task2/imbalance_comparison.csv.

### Câu hỏi 10 Tại sao không dùng SMOTE?

Trả lời ngắn: Balanced weight tăng chi phí của lỗi ở lớp ít ví dụ.

Giải thích sâu: Validation cho thấy neutral recall tăng từ 0,093023 lên 0,488372 và neutral F1 tăng từ 0,170213 lên 0,471910 khi dùng balanced. Precision neutral giảm từ 1 xuống 0,456522: mô hình tìm thêm neutral nhưng cũng tạo false positives. Đây là trade-off có đo đạc, không phải lời khẳng định mọi lớp đều tốt hơn.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Không có SMOTE experiment để tuyên bố nó kém.

Evidence và file/code để mở: src/baselines/tfidf_logreg.py; reports/task2/imbalance_comparison.csv.

### Câu hỏi 11 Foody có ground truth sentiment không?

Trả lời ngắn: Nguồn demo hiện hành là data/foody/source/foody_reviews.csv, không phải review.csv lịch sử.

Giải thích sâu: Một observation gộp restaurant_key với text chuẩn hóa để tránh dự đoán lặp. Một review_id còn gồm User, thời gian thô và Comment gốc, vì vậy các người/ngày khác nhau có thể chia sẻ một lần suy luận nhưng vẫn là review khác. Marts/RAG dùng distinct review_id; processed/enriched giữ tất cả source rows. restaurant_key tạo từ tên chuẩn hóa, không phải official ID; trùng tên chi nhánh vẫn là rủi ro.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Prediction và confidence không phải measured accuracy.

Evidence và file/code để mở: src/foody/cleaning.py; src/foody/schema.py; reports/foody_intelligence/cleaning.json.

### Câu hỏi 12 31.694 và 32.457 khác nhau thế nào?

Trả lời ngắn: Nguồn demo hiện hành là data/foody/source/foody_reviews.csv, không phải review.csv lịch sử.

Giải thích sâu: Một observation gộp restaurant_key với text chuẩn hóa để tránh dự đoán lặp. Một review_id còn gồm User, thời gian thô và Comment gốc, vì vậy các người/ngày khác nhau có thể chia sẻ một lần suy luận nhưng vẫn là review khác. Marts/RAG dùng distinct review_id; processed/enriched giữ tất cả source rows. restaurant_key tạo từ tên chuẩn hóa, không phải official ID; trùng tên chi nhánh vẫn là rủi ro.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Observation ID khác review ID.

Evidence và file/code để mở: src/foody/cleaning.py; src/foody/schema.py; reports/foody_intelligence/cleaning.json.

## Tài liệu ngoài repository

External literature/documentation giải thích phương pháp hoặc kiến trúc model; mọi điểm số nhóm trong tài liệu đến từ saved experiment. Không có paper macro-F1 trực tiếp tương đương trên frozen 887-row test. Không gán năm công bố nếu nguồn không chứng minh.

VN-MSASar v3 dataset card. phamluan. không xác định năm công bố từ provenance; truy cập 2026-10-22. https://huggingface.co/datasets/phamluan/vn_msa_sar_v3

TfidfVectorizer 1.7.2 API. scikit-learn developers. 2025 version 1.7.2; truy cập 2026-10-22. https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html

LogisticRegression 1.7.2 API. scikit-learn developers. 2025 version 1.7.2; truy cập 2026-10-22. https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html

SQLite FTS5 bm25 function. SQLite developers. tài liệu cập nhật liên tục; truy cập 2026-10-22. https://www.sqlite.org/fts5.html#the_bm25_function

paraphrase multilingual MiniLM L12 v2 model card. Sentence Transformers. model card không dùng làm nguồn số liệu project; truy cập 2026-10-22. https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

Qwen2.5 3B Instruct GGUF model card. Qwen team. 2024 model family; truy cập 2026-10-22. https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF

Llama 3.2 3B Instruct model card. Meta. 2024 model family; truy cập 2026-10-22. https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct

DeepSeek R1 Distill Qwen 1.5B model card. DeepSeek AI. 2025 model family; truy cập 2026-10-22. https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B

CI đã xác minh: https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39739640437

Release đã xác minh: https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39742439011
