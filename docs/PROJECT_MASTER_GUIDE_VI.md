# Hướng dẫn toàn bộ Food Review Intelligence bằng tiếng Việt

Tài liệu học và bảo vệ thiết kế kỹ thuật

End-to-End Food Review Intelligence & LLMOps Platform

Ngày lập tài liệu 22/10/2026. Source snapshot 4229a8b3998392c97f4b7a8c9e3795830285dbce.

Tài liệu phân biệt MEASURED (đo đã lưu), DERIVED (tính lại), CONFIGURED (tham số code/config), EXTERNAL (nguồn ngoài). THEORY và EXAMPLE không phải kết quả project. Các đường dẫn source tính từ thư mục gốc repository.

<!-- TOC -->

Mục tiêu đọc: hiểu bài toán, lần theo dữ liệu và code, tính lại chỉ số và giải thích quyết định. Đọc chương1–25 cho dữ liệu/ML,26–52 cho RAG/LLM,53–69 cho vận hành và70–85 để tra cứu/bảo vệ. Kết quả nổi bật là classifier TF-IDF được chọn cho sentiment, Qwen3B phục vụ RAG có evidence gates, và24/24 checklist đã có evidence với các giới hạn khoa học giữ nguyên.

## Chương 1 Bài toán và giá trị sử dụng

Người quản lý nhà hàng cần biết khách đang khen hoặc phàn nàn điều gì, tại chi nhánh nào và trong khoảng thời gian nào. Khi hàng nghìn nhận xét nằm rải rác trong file xuất, đọc từng dòng khó tạo được một bức tranh nhất quán. Hệ thống chuẩn hóa dữ liệu, bổ sung dự đoán sentiment và aspect, tạo bảng tổng hợp, rồi cho phép hỏi bằng tiếng Việt với bằng chứng review đi kèm.

Có hai luồng độc lập. VN-MSASar cung cấp nhãn nghiên cứu để huấn luyện và đánh giá classifier; Foody là dữ liệu thực tế để suy luận, dashboard và RAG. Kết quả tốt trên VN-MSASar không tự biến thành accuracy trên Foody. Sản phẩm là demo chạy local đã nghiệm thu, chưa có bằng chứng triển khai production từ xa.

Luồng nghiệp vụ: Review → kiểm tra và làm sạch → sentiment → aspect → issue heuristic → restaurant marts và tài liệu RAG → truy xuất → evidence packet → LLM → kiểm tra căn cứ → Streamlit. Người dùng thấy cả chế độ trả lời và nguồn trích dẫn để đánh giá mức chắc chắn.
Nguồn: README.md; src/foody/pipeline.py; app/app.py; reports/task2/TRAINING_SCOPE.md.

## Chương 2 Lịch sử phát triển và quyết định qua từng giai đoạn

Hướng ban đầu là Shopee crawler và Databricks. Những module còn tồn tại phục vụ kiểm thử và audit lịch sử, không phải đường demo hiện hành. Cần ghi đúng: Historical experiment — not current production path. Repository sau đó chuyển sang review nhà hàng Việt Nam và đóng băng dataset trước khi so sánh phương pháp.

Baseline rule kiểm tra mức có thể đạt bằng từ điển thủ công. TF-IDF LR học mẫu từ/cụm từ từ train và vượt rule. Giả thuyết LLM prompt có thể tốt hơn được thử ở Qwen V1; kết quả macro-F1 thấp hơn TF-IDF dẫn đến V2-A hiệu chỉnh prompt. V2-A không cải thiện; nghiên cứu text+aspect là V2-B riêng, cũng không thay thế classifier đã chọn.

Đối với demo, vấn đề chuyển sang tìm và diễn đạt bằng chứng. RAG V1 dùng dense; V2 bổ sung BM25, RRF và quy tắc evidence; V3 định tuyến, chuẩn bị packet trước sinh và có fallback. Streamlit trình bày dữ liệu, LLMOps ghi vận hành; Docker và CI/CD xác minh khả năng đóng gói. Chuỗi này là tiến trình đổi bài toán và rút kinh nghiệm, không phải một bảng accuracy liên tục từ sentiment sang RAG.
Nguồn: reports/final/TASK2_EXPERIMENT_STORY.md; docs/experiments/; reports/task2/RAG_ABLATION_FINAL.md.

## Chương 3 Dataset VN MSASar v3

Nguồn public là phamluan/vn_msa_sar_v3 trên Hugging Face, revision 6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4, license CC BY 4.0 theo provenance. Ba file nguồn có tổng 76.785 dòng. Adapter chỉ giữ language=vi và place_type=restaurant, còn 5.869 dòng hợp lệ; không có dòng bị reject hoặc duplicate bị loại ở lần chuẩn bị đã lưu.

Một dòng biểu diễn câu và aspect được gán nhãn, không nhất thiết là một review độc lập. Có 1.530 review_id và 5.316 câu chuẩn hóa riêng biệt. Schema nguồn gồm review_id, source, place_type, language, sentence, aspect, sentiment, sarcasm. Adapter đổi sentence thành text, giữ original_text và original_sentiment, lưu metadata provenance. research source=foody không có nghĩa là cùng export Foody first-party dùng cho demo.

Hãy đọc bảng phân bố phía dưới cùng đơn vị đếm. food xuất hiện nhiều vì mỗi dòng mang một aspect; aspect classifier sau này gộp những dòng có cùng text thành target nhiều nhãn. Không cộng số research rows với RAG documents thành một tập train chung.
Nguồn: reports/food_dataset_report.json; src/food/adapters.py; data/food/source/vn_msasar_v3/provenance.json.

Bảng 1. Phân bố aspect research rows

| Aspect | Rows |
| --- | --- |
| food | 2413 |
| service | 1031 |
| price | 878 |
| overall | 703 |
| ambiance | 483 |
| location | 193 |
| cleanliness | 139 |
| amenities | 20 |
| room | 9 |

Nguồn: reports/food_dataset_report.json. Loại: MEASURED.

![Nguồn dữ liệu và phân bố lớp](../reports/task2/figures/dataset_class_distribution.png)

Hình 1. Nguồn dữ liệu và phân bố lớp. Nguồn: reports/task2/figures/dataset_class_distribution.png.

## Chương 4 Chuẩn hóa nhãn cảm xúc

Thang sentiment nguồn là số nguyên từ −3 đến +3. Hàm ordinal kiểm tra số hữu hạn, nguyên và nằm trong tập cho phép; boolean, NaN hoặc giá trị ngoài miền bị loại. LABEL_MAPPING ánh xạ số âm thành negative, 0 thành neutral và số dương thành positive. Đây là phép gộp độ mạnh theo dấu, không phải chuyển rating sao thành sentiment.

THEORY: negative biểu đạt không hài lòng; positive biểu đạt hài lòng; neutral là trung tính theo nhãn nguồn. EXAMPLE: −2 và −1 cùng trở thành negative, +1 và +3 cùng positive. PROJECT RESULT: original_sentiment được giữ để truy vết; ba nhãn được dùng nhất quán trong metrics. Gộp nhãn làm bài toán đơn giản hơn nhưng mất thông tin cường độ và vẫn không giải quyết câu có cảm xúc khác nhau theo aspect.
Nguồn: src/food/adapters.py::ordinal và LABEL_MAPPING; reports/food_label_mapping.json.

## Chương 5 Train validation test và kiểm soát leakage

Train dùng để fit vocabulary, IDF và trọng số classifier. Validation chọn cấu hình/prompt. Test chỉ đánh giá cấu hình đã đóng băng. Đưa một phần câu test vào quá trình fit làm mô hình biết trước đặc điểm tập đánh giá và tạo ước lượng lạc quan.

assign_splits không chia từng dòng độc lập: leakage_groups dùng thành phần liên thông nối các dòng chung review_id hoặc text chuẩn hóa. Vì thế một review hoặc câu giống hệt không đi vào nhiều split. Thuật toán tìm 64 phương án GroupShuffleSplit theo seed 42 rồi chọn phương án gần tỷ lệ và phân bố lớp mong muốn; đây là tìm split bằng nhãn, không phải chọn theo điểm dự đoán test. Tỷ lệ thực không đúng tuyệt đối 70/15/15 do ràng buộc nhóm.

PROJECT RESULT: 4.140 train, 842 validation, 887 test; tương ứng 1.074, 229, 227 review IDs. Có 1.481 thành phần liên thông. Kiểm tra ID và normalized text giao nhau đều bằng 0; near-duplicate gần giống chưa được đảm bảo. V2 và ba-seed dùng lại test đã nhìn thấy phải mang nhãn exploratory.
Nguồn: src/food/split.py::leakage_groups, assign_splits, load_splits; data/food/splits/metadata.json.

Bảng 2. Split và số đếm

| Split | Rows | Review IDs | Negative | Neutral | Positive |
| --- | --- | --- | --- | --- | --- |
| train | 4140 | 1074 | 1307 | 208 | 2625 |
| validation | 842 | 229 | 270 | 43 | 529 |
| test | 887 | 227 | 284 | 43 | 560 |

Nguồn: data/food/splits/metadata.json. Loại: MEASURED.

## Chương 6 Mất cân bằng lớp

Positive chiếm 3.714 dòng, negative 1.861 và neutral 294. Class imbalance nghĩa là số ví dụ giữa các lớp chênh lệch; mô hình có thể ưu tiên lớp đông và vẫn có accuracy khá. Vì thế macro-F1, lấy trung bình công bằng theo lớp, phù hợp để chọn sentiment classifier trong project.

DERIVED: imbalance ratio = 3.714 / 294 = 12,632653. Neutral chiếm 294 / 5.869 × 100 = 5,009371%. Tỷ lệ này mô tả toàn bộ tập nghiên cứu, không phải weight tính khi train. Class weighting không thay đổi biểu đồ số dòng nên không có một phân bố sample sau cân bằng mới.
Nguồn: reports/task2/class_distribution.csv; reports/food_dataset_report.json.

Bảng 3. Phân bố sentiment

| Class | Rows | % |
| --- | --- | --- |
| negative | 1861 | 31.708979 |
| neutral | 294 | 5.009371 |
| positive | 3714 | 63.281649 |

Nguồn: reports/task2/class_distribution.csv. Loại: MEASURED.

![Class imbalance trên research dataset](../reports/task2/figures/class_distribution.png)

Hình 2. Class imbalance trên research dataset. Nguồn: reports/task2/figures/class_distribution.png.

## Chương 7 Class weight và lý do không dùng SMOTE

Balanced weight tăng chi phí của lỗi ở lớp ít ví dụ. Với N=4.140 và K=3, weight_j=N/(K×n_j). Train negative=1.307 cho weight 1,055853; neutral=208 cho 6,634615; positive=2.625 cho 0,525714. Các giá trị được tính lại bằng script tài liệu, không chỉnh training.

Validation cho thấy neutral recall tăng từ 0,093023 lên 0,488372 và neutral F1 tăng từ 0,170213 lên 0,471910 khi dùng balanced. Precision neutral giảm từ 1 xuống 0,456522: mô hình tìm thêm neutral nhưng cũng tạo false positives. Đây là trade-off có đo đạc, không phải lời khẳng định mọi lớp đều tốt hơn.

SMOTE không được dùng. Nội suy vector TF-IDF sparse không tương đương tạo review tiếng Việt tự nhiên, còn weighting tác động trực tiếp hàm mất mát và giữ nguyên membership. Repository không có thử nghiệm SMOTE đối chứng, nên không kết luận SMOTE chắc chắn kém hơn.
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

Hình 3. Validation trước và sau balanced weights. Nguồn: reports/task2/figures/imbalance_effect.png.

## Chương 8 Foody và ý nghĩa từng loại số đếm

Nguồn demo hiện hành là data/foody/source/foody_reviews.csv, không phải review.csv lịch sử. First-party ownership là thông tin người dùng cung cấp; checksum chỉ chứng minh snapshot trùng byte, không tự chứng minh quyền sở hữu hoặc tính đại diện. Có 33.946 dòng thô, 33.938 dòng hợp lệ cho AI, 31.694 observation suy luận sau gộp và 32.457 review_id hợp lệ riêng biệt, thuộc 2.110 restaurant_key.

Một observation gộp restaurant_key với text chuẩn hóa để tránh dự đoán lặp. Một review_id còn gồm User, thời gian thô và Comment gốc, vì vậy các người/ngày khác nhau có thể chia sẻ một lần suy luận nhưng vẫn là review khác. Marts/RAG dùng distinct review_id; processed/enriched giữ tất cả source rows. restaurant_key tạo từ tên chuẩn hóa, không phải official ID; trùng tên chi nhánh vẫn là rủi ro.

Ngày nguồn từ 2011-01-09 12:07:32 đến 2026-10-14 15:46:56, rating 0–10. Một comment rỗng và bảy comment chứa U+FFFD bị loại khỏi AI, không sửa đoán chữ. Dấu hỏi kép là cờ chẩn đoán, không tự động là lỗi encoding. Export hiện hành không có Classification và không có sentiment/aspect gold đáng tin cậy; mọi nhãn bổ sung là dự đoán.
Nguồn: src/foody/cleaning.py; src/foody/schema.py; reports/foody_intelligence/cleaning.json.

Bảng 5. Các đơn vị đếm Foody

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

## Chương 9 Data marts phục vụ quản lý nhà hàng

Data mart là bảng đã tổng hợp cho một câu hỏi nghiệp vụ. restaurant_summary cho số review, rating trung bình và tỷ lệ sentiment; restaurant_daily_metrics và restaurant_monthly_metrics thêm trục thời gian; restaurant_aspect_summary và restaurant_issue_summary cho phân bố nhãn dự đoán; alerts giữ các thay đổi vượt ngưỡng.

business_rows loại trùng review_id trước tổng hợp. Mẫu số của sentiment là review hợp lệ có prediction; mẫu số rating chỉ gồm numeric rating trong [0,10]. Complaint rate kết hợp overall negative và aspect presence, không phải xác suất aspect-level sentiment gold. Một review nhiều aspect có thể đóng góp vào nhiều tỷ lệ, nên không buộc tổng tỷ lệ aspect bằng 100%.

alerts so sánh hai tháng lịch liền kề với ít nhất 10 mẫu mỗi kỳ, chênh tỷ lệ ≥0,2 hoặc rating giảm ≥1,0. Tháng cuối bị bỏ khỏi so sánh vì có thể chưa đủ tháng. Các ngưỡng là engineering choice, chưa có tối ưu có kiểm soát. Đây là cảnh báo lịch sử, không chứng minh nguyên nhân suy giảm hay tình trạng hiện tại.
Nguồn: src/foody/analytics.py; reports/foody_intelligence/mart.json.

## Chương 10 Sentiment analysis từ đầu

Sentiment analysis ánh xạ văn bản sang thái độ cảm xúc. Trong bài toán này một text chỉ nhận một trong ba nhãn negative, neutral, positive. Các từ ngon, tệ có thể là tín hiệu, nhưng phủ định, mỉa mai, ngữ cảnh và câu nhiều ý làm quan hệ từ–nhãn không đơn giản.

EXAMPLE: “Món ngon nhưng phục vụ chậm” chứa khen food và chê service. Nếu chỉ đưa text, mô hình không biết người đánh giá muốn sentiment của aspect nào. PROJECT RESULT: có 81 normalized texts mang gold sentiment xung đột toàn tập, 11 trong test. Đây là giới hạn thông tin của protocol text-only, không thể sửa bằng đổi nhãn cho thuận lợi.
Nguồn: src/baselines/runner.py; reports/baselines/failure_analysis_summary.json; reports/task2/GAP_ANALYSIS.md.

## Chương 11 Baseline rule based

VietnameseRuleBased tách token và dấu câu; khớp cụm lexicon dài nhất không chồng lấp. Từ/cụm tích cực đóng góp +1, tiêu cực −1. Số lượng phủ định lẻ trong ba token trước đảo dấu; punctuation hoặc từ đối lập kết thúc phạm vi. Intensifier nhân đóng góp với 1,5. Tổng dương → positive, âm → negative, bằng 0 → neutral.

EXAMPLE: “không ngon” đảo tín hiệu ngon thành âm. “rất ngon nhưng chậm” có thể cộng 1,5 và −1, ra positive: đó là hành vi của quy tắc, không bảo đảm đúng nhãn aspect. Rule không học trọng số và không đọc gold, rating hoặc aspect. Nó dễ giải thích và nhanh nhưng thiếu từ vựng, thành ngữ và sarcasm.

PROJECT RESULT: accuracy 0,505073; macro-F1 0,431279; neutral recall cao nhưng precision thấp do nhiều câu không khớp lexicon rơi về neutral. Đây là baseline tham chiếu thấp, không phải thuật toán được tái lập từ một paper có cùng split.
Nguồn: src/baselines/rule_based.py; reports/baselines/rule_based_test_metrics.json.

## Chương 12 TF IDF và biểu diễn văn bản

TF-IDF chuyển câu thành vector mà mỗi chiều ứng với một token hoặc n-gram trong vocabulary train. TF phản ánh tần suất trong văn bản; IDF giảm trọng số từ xuất hiện trong nhiều văn bản. Vector sparse lưu chủ yếu giá trị khác 0, phù hợp câu ngắn và vocabulary lớn.

THEORY: cách giới thiệu phổ biến dùng TF=count/độ dài và IDF=ln(N/df). PROJECT CONFIG: TfidfVectorizer dùng sublinear_tf=True nên TF=1+ln(count) khi count>0; smooth_idf mặc định cho IDF=ln((1+N)/(1+df))+1, sau đó chuẩn hóa L2. Không được lấy công thức TF chuẩn hóa độ dài làm mô tả chính xác implementation.

EXAMPLE: “món ăn rất ngon nhưng phục vụ chậm” cho unigram món, ăn, rất... và bigram món ăn, ăn rất, rất ngon... Token pattern cho phép cả từ một ký tự; không có word segmentation tiếng Việt chuyên biệt. Bigrams giúp giữ một phần ngữ cảnh nhưng tăng vocabulary; IDF chỉ fit trên train.
Nguồn: src/baselines/tfidf_logreg.py::build_pipeline; tài liệu TfidfVectorizer scikit-learn 1.7.

## Chương 13 Các tham số TF IDF và bằng chứng lựa chọn

Ba trial thật là unigram C=1, unigram+bigram C=1 và unigram+bigram C=2. Validation macro-F1 lần lượt 0,648722; 0,700294; 0,709242. Trial thứ ba được chọn theo max validation macro-F1; stable candidate order xử lý hòa. Đây là bằng chứng lựa chọn trong tập ba ứng viên, không phải chứng minh tối ưu toàn bộ không gian.

max_features=20.000 giới hạn vocabulary, min_df=2 bỏ token xuất hiện trong ít hơn hai document train, sublinear_tf=True giảm ưu thế từ lặp. max_iter=1.500 là trần solver, lbfgs là solver sentiment, random_state=42 cố định protocol. Các giá trị này không có sweep độc lập trong repo. Tăng vocabulary có thể giữ tín hiệu hiếm nhưng tăng kích thước và overfit; tăng min_df giảm nhiễu nhưng có thể mất slang hiếm.

Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu. Câu này áp dụng cho từng tham số cố định chưa có đối chứng, không áp dụng thay cho bảng trial n-gram/C đã có.
Nguồn: reports/baselines/tfidf_experiments.csv; src/baselines/tfidf_logreg.py.

Bảng 6. Chọn cấu hình sentiment trên validation

| Trial | Ngrams | C | Val accuracy | Val macro F1 |
| --- | --- | --- | --- | --- |
| A_unigram_c1 | (1, 1) | 1 | 0.767221 | 0.648722 |
| B_bigram_c1 | (1, 2) | 1 | 0.812352 | 0.700294 |
| C_bigram_c2 | (1, 2) | 2 | 0.819477 | 0.709242 |

Nguồn: reports/baselines/tfidf_experiments.csv. Loại: MEASURED.

## Chương 14 Logistic Regression

Một classifier tuyến tính tính score z=wᵀx+b. x là vector TF-IDF; w học từ train; b là bias. Với hai lớp, sigmoid đổi score thành xác suất. Với ba lớp của sentiment và solver lbfgs ở scikit-learn 1.7.2, cách giải thích đúng là multinomial softmax: mỗi lớp có score riêng, rồi exp(score) được chuẩn hóa bằng tổng exp của mọi lớp.

Training tối ưu hàm mất mát có regularization và class weights. predict chọn lớp có xác suất lớn nhất, predict_proba cung cấp vector xác suất. Decision boundary là nơi score của hai lớp bằng nhau. Các xác suất này chưa được calibration trên Foody; giá trị 0,9 không tự chứng minh 90% đúng trong miền dữ liệu mới.

Aspect classifier là trường hợp khác: OneVsRest tạo bài toán nhị phân độc lập cho từng aspect với solver liblinear và threshold. Không trộn softmax của sentiment với sigmoid của OVR.
Nguồn: src/baselines/tfidf_logreg.py; src/foody/aspect.py; tài liệu LogisticRegression scikit-learn 1.7.

## Chương 15 Regularization và C

Regularization hạn chế nghiệm quá phụ thuộc các mẫu train. C là nghịch đảo mức regularization: C nhỏ phạt trọng số mạnh hơn, C lớn cho phép fit linh hoạt hơn. Không diễn giải C=2 là learning rate hay số lớp. Penalty mặc định của cấu hình đang dùng là L2.

PROJECT RESULT: trong cặp cùng bigram, đổi C=1 sang 2 tăng validation macro-F1 từ 0,700294 lên 0,709242. Chỉ có bằng chứng cho hai điểm đó; không suy ra C=10 sẽ tốt hơn. Mô hình được fit train rồi chọn bằng validation, không refit train+validation trước test trong protocol đã lưu.
Nguồn: src/baselines/runner.py; reports/baselines/tfidf_experiments.csv; reports/baselines/tfidf_selection.json.

## Chương 16 Metrics và đọc confusion matrix

Confusion matrix có hàng là gold và cột là predicted. Với một lớp đang xét, TP là đúng lớp đó; FP là lớp khác bị dự đoán thành nó; FN là lớp đó bị bỏ sót. Accuracy đếm đúng trên tổng; precision hỏi “những dự đoán lớp này đáng tin đến đâu”; recall hỏi “tìm được bao nhiêu ví dụ thực của lớp này”. F1 là trung bình điều hòa precision/recall.

Macro-F1 lấy trung bình F1 từng lớp, không phải F1 tính từ macro-precision và macro-recall. Weighted-F1 dùng support làm trọng số nên lớp positive đông có ảnh hưởng lớn. Micro-F1 gom TP/FP/FN trước khi tính; trong single-label đủ nhãn nó bằng accuracy, nhưng trong multi-label không còn như vậy. zero_division=0 xử lý mẫu số bằng 0 trong code.

EXAMPLE: ma trận minh họa và tính tay nằm trong phụ lục công thức; được ghi rõ không phải kết quả project. PROJECT RESULT: confusion TF-IDF thật được đọc trực tiếp từ JSON để tính lại accuracy, precision, recall và F1, không chạy lại model.
Nguồn: src/baselines/metrics.py::scores, class_report; reports/baselines/tfidf_test_metrics.json.

Bảng 7. Confusion minh họa không phải số liệu project

| Gold / Pred | negative | neutral | positive |
| --- | --- | --- | --- |
| negative | 8 | 1 | 1 |
| neutral | 2 | 5 | 3 |
| positive | 1 | 1 | 8 |

Nguồn: Ví dụ minh họa tự dựng. Loại: EXAMPLE.

Ví dụ: accuracy=(8+5+8)/30=0,7. Neutral TP=5, FP=2, FN=5; P=5/7, R=5/10, F1=10/17≈0,588235. Không dùng các số này trong bảng kết quả project.

Bảng 8. Confusion TF IDF thật

| Gold / Pred | negative | neutral | positive |
| --- | --- | --- | --- |
| negative | 228 | 9 | 47 |
| neutral | 10 | 19 | 14 |
| positive | 68 | 21 | 471 |

Nguồn: reports/baselines/tfidf_test_metrics.json. Loại: MEASURED.

## Chương 17 Kết quả baseline và chọn classifier triển khai

Rule-Based đạt test accuracy 0,505073, macro-F1 0,431279. TF-IDF LR đạt 0,809470 và 0,682854. TF-IDF neutral F1 là 0,413043, vẫn yếu hơn negative/positive. Accuracy cao hơn chưa đủ; macro-F1 và per-class report xác nhận cải thiện có ý nghĩa đối với mục tiêu ba lớp.

Classifier TF-IDF được dùng trong Foody inference vì kết quả đã đo tốt hơn Qwen V1 cho phân loại text-only, latency trung bình single-sample 0,365186 ms và artifact 0,342442 MB. Các timing này là run local riêng, không phải SLA production hoặc speedup đối chứng trên mọi thiết bị. Qwen đảm nhiệm sinh câu từ bằng chứng, một năng lực khác với gán nhãn.
Nguồn: reports/baselines/baseline_comparison.csv; reports/task2/FEASIBILITY.csv; src/foody/enrichment.py.

Bảng 9. Sentiment test metrics cùng frozen split

| Model | Accuracy | Macro P | Macro R | Macro F1 | Weighted F1 |
| --- | --- | --- | --- | --- | --- |
| Rule | 0.505073 | 0.619395 | 0.596898 | 0.431279 | 0.592298 |
| TF-IDF LR | 0.809470 | 0.672730 | 0.695250 | 0.682854 | 0.812104 |
| Qwen V1 | 0.732807 | 0.632795 | 0.733282 | 0.621789 | 0.774715 |
| Qwen V2-A exploratory | 0.723788 | 0.646854 | 0.728008 | 0.614487 | 0.778542 |

Nguồn: reports/baselines/*test_metrics.json; reports/proposed_v1/qwen_test_metrics.json; reports/proposed_v2/test_metrics.json. Loại: MEASURED.

![Baseline và proposed sentiment](../reports/task2/figures/baseline_comparison.png)

Hình 4. Baseline và proposed sentiment. Nguồn: reports/task2/figures/baseline_comparison.png.

## Chương 18 Độ ổn định ba seed

Seed điều khiển các bước ngẫu nhiên; không phải mọi solver đều nhạy với seed. Ba lần train so sánh dùng seed 42, 123, 2026 trên cùng frozen membership và cùng cấu hình đã chấp nhận. Artifact classifier demo không bị ghi đè bởi nghiên cứu này.

PROJECT RESULT: cả ba có test macro-F1 0,682854, accuracy 0,809470, weighted-F1 0,812104 và neutral F1 0,413043; sample SD bằng 0. Điều đó phù hợp lbfgs gần như xác định trong setup này. Không được suy ra độ bất định bằng 0 trên các split hoặc domain khác; chỉ random_state được thay trong phép lặp này.

LinearSVC là so sánh bổ sung: validation chọn C=0,5 trong {0,5;1;2}; test macro-F1 0,667210 thấp hơn LR dù accuracy 0,818489 cao hơn. Đây là ví dụ chọn theo accuracy có thể đưa ra quyết định khác với macro-F1.
Nguồn: reports/task2/baseline_three_seed.csv; reports/task2/linearsvc_validation_selection.csv; scripts/task2_classical_comparison.py.

Bảng 10. Ba seed trên cùng membership

| Seed | Split | Accuracy | Macro F1 | Weighted F1 | Neutral F1 |
| --- | --- | --- | --- | --- | --- |
| 42 | validation | 0.819477 | 0.709242 | 0.821549 | 0.471910 |
| 42 | test | 0.809470 | 0.682854 | 0.812104 | 0.413043 |
| 123 | validation | 0.819477 | 0.709242 | 0.821549 | 0.471910 |
| 123 | test | 0.809470 | 0.682854 | 0.812104 | 0.413043 |
| 2026 | validation | 0.819477 | 0.709242 | 0.821549 | 0.471910 |
| 2026 | test | 0.809470 | 0.682854 | 0.812104 | 0.413043 |

Nguồn: reports/task2/baseline_three_seed.csv. Loại: MEASURED.

Bảng 11. LinearSVC supplemental selection

| C | Val accuracy | Val macro F1 | Val neutral F1 |
| --- | --- | --- | --- |
| 0.500000 | 0.836105 | 0.701795 | 0.424242 |
| 1 | 0.830166 | 0.692742 | 0.412698 |
| 2 | 0.828979 | 0.689493 | 0.406250 |

Nguồn: reports/task2/linearsvc_validation_selection.csv. Loại: MEASURED.

## Chương 19 Qwen Proposed V1

V1 dùng Qwen2.5-1.5B-Instruct-GGUF Q4_K_M, chạy llama.cpp b11429. Model là bộ trọng số đã tiền huấn luyện; runtime là phần mềm thực thi trọng số. GGUF là định dạng; Q4_K_M là cấu hình quantization hỗn hợp trong họ K-quant, không phải mọi tensor đều chính xác bốn bit. Không có fine-tuning hoặc training LLM from scratch.

Ba prompt đóng băng: v1_a tối giản, v1_b định nghĩa nhãn, v1_c thêm ba ví dụ train-only không xung đột. Chọn bằng validation macro-F1, rồi JSON validity và latency. Qwen chỉ nhận text, phải trả JSON sentiment thuộc ba nhãn. Temperature=0, seed=42, output cap=32, tối đa hai attempts; parser/schema không âm thầm đổi free text thành label.

v1_c được chọn với validation macro-F1 0,641252. Test 887 mẫu cho macro-F1 0,621789, accuracy 0,732807 và JSON validity 1. JSON hợp lệ chỉ chứng minh định dạng, không chứng minh phân loại đúng. Tài nguyên đỉnh của evaluation V1 bị mất trong lỗi reporting; probe idle về sau không thay thế được peak inference.
Nguồn: qwen_v1.yaml; src/proposed_v1/runner.py; reports/proposed_v1/qwen_prompt_comparison.csv; reports/proposed_v1/qwen_resource_report.json.

Bảng 12. Prompt V1 selection

| Prompt | Val macro F1 | JSON rate | Mean ms | Input tokens | Output tokens |
| --- | --- | --- | --- | --- | --- |
| v1_a | 0.589172 | 1 | 66.254108 | 79349 | 5894 |
| v1_b | 0.626862 | 1 | 75.553218 | 152603 | 5894 |
| v1_c | 0.641252 | 1 | 93.411746 | 237645 | 5894 |

Nguồn: reports/proposed_v1/qwen_prompt_comparison.csv. Loại: MEASURED.

## Chương 20 Phân tích lỗi Proposed V1

V1 sai 237/887 mẫu; TF-IDF sai 169. Neutral V1 recall 0,674419 nhưng precision chỉ 0,159341: mô hình bắt được 29/43 gold-neutral nhưng dự đoán neutral quá nhiều. F1 0,257778 thấp hơn TF-IDF 0,413043. Không thể dùng recall đơn lẻ để tuyên bố neutral được cải thiện.

failure_counts cho sarcasm 9 lỗi trên 37 mẫu, mixed-marker 45/121, negation-marker 42/208, short text 33/93 và conflicting text 16/24. Các nhóm chồng lấp; chỉ sarcasm lấy nhãn nguồn, các marker khác là proxy lexical. Không cộng các tử số thành tổng lỗi và không coi proxy là annotation thủ công về hiện tượng ngôn ngữ.

DERIVED: macro-F1 V1 − rule = +0,190510; V1 − TF-IDF = −0,061065; neutral F1 V1 − TF-IDF = −0,155266. Có improvement so với rule, không có improvement so với baseline mạnh đã chọn. Thất bại này thúc đẩy thử prompt calibration và aspect input thay vì thay nhãn test.
Nguồn: reports/task2/failure_counts.csv; reports/proposed_v1/qwen_test_metrics.json; reports/baselines/tfidf_classification_report.csv.

Bảng 13. Failure taxonomy và mẫu số

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

## Chương 21 V2 calibration và nghiên cứu aspect conditioned

V2-A vẫn text-only. Ba prompt v2_a1/a2/a3 dùng 6/9/8 ví dụ train, hiệu chỉnh cách hiểu neutral và các trường hợp sai ở validation V1. Chọn v2_a3 bằng validation macro-F1 0,632579. Test macro-F1 0,614487 và neutral F1 0,247104 đều thấp hơn V1 và TF-IDF. Vì test V1 đã được xem, kết quả V2 phải ghi exploratory reused test.

V2-B ở src/aspect_conditioned là protocol khác: text+aspect. Qwen text+aspect test macro-F1 0,602203; TF-IDF text+aspect 0,665514. Không được gọi V2-A là aspect-conditioned như một câu trong GAP_ANALYSIS/Q&A cũ. Hai protocol cần cột input riêng và không được dùng kết quả này làm benchmark text-only công bằng tuyệt đối.

Scientific lesson: prompt dài hơn, nhiều ví dụ hơn hoặc đầu vào giàu hơn không bảo đảm cải thiện. Tăng latency và token khi metric không tăng là bằng chứng chưa nên thay model demo. Một tập test ngoài chưa đụng tới vẫn cần cho xác nhận tiếp theo.
Nguồn: qwen_v2.yaml; qwen_aspect.yaml; reports/proposed_v2/prompt_comparison.csv; reports/aspect_conditioned/comparison.csv.

Bảng 14. V2 A calibration

| Prompt | Train examples | Val macro F1 | Val neutral F1 | Mean ms |
| --- | --- | --- | --- | --- |
| v2_a1 | 6 | 0.623801 | 0.274194 | 110.991605 |
| v2_a2 | 9 | 0.623353 | 0.271493 | 135.550636 |
| v2_a3 | 8 | 0.632579 | 0.283019 | 287.467406 |

Nguồn: reports/proposed_v2/prompt_comparison.csv. Loại: MEASURED.

![V1 và V2 sentiment](../reports/task2/figures/v1_v2_sentiment_comparison.png)

Hình 5. V1 và V2 sentiment. Nguồn: reports/task2/figures/v1_v2_sentiment_comparison.png. Test V2 reused và exploratory.

## Chương 22 Aspect classification nhiều nhãn

Sentiment là multi-class: mỗi dòng một nhãn. Aspect là multi-label: một câu có thể cùng nói food, service và price. grouped_targets chuẩn hóa text rồi lấy hợp các aspect đã được annotation trong cùng split. Số đơn vị đánh giá đổi thành 3.768 train, 751 validation, 797 test; không chia lại membership.

Pipeline gồm TF-IDF unigram+bigram và OneVsRest Logistic Regression. Mỗi aspect có classifier nhị phân độc lập. Giá trị predict_proba ≥ threshold được chọn, cho phép không nhãn hoặc nhiều nhãn. C∈{0,5;2}, threshold∈{0,3;0,5;0,7}; chọn C=2, threshold=0,5 theo validation micro-F1, sau đó macro-F1 và C nhỏ hơn.

Aspect không được annotation bị coi là negative trong benchmark, dù annotation có thể thiếu. Không được mô tả target này như danh sách mọi aspect chắc chắn có trong câu. Model riêng giúp dashboard trả lời review đang nói về chuyện gì nhưng không tự đo sentiment của từng aspect.
Nguồn: src/foody/aspect.py; reports/aspect_classifier/selection.json; reports/aspect_classifier/validation_comparison.csv.

Bảng 15. Aspect validation search

| C | Threshold | Micro P | Micro R | Micro F1 | Macro F1 |
| --- | --- | --- | --- | --- | --- |
| 0.500000 | 0.300000 | 0.466474 | 0.958432 | 0.627527 | 0.460418 |
| 0.500000 | 0.500000 | 0.831695 | 0.804038 | 0.817633 | 0.608279 |
| 0.500000 | 0.700000 | 0.939052 | 0.494062 | 0.647471 | 0.514724 |
| 2 | 0.300000 | 0.650126 | 0.918052 | 0.761201 | 0.558828 |
| 2 | 0.500000 | 0.836408 | 0.807601 | 0.821752 | 0.612648 |
| 2 | 0.700000 | 0.919866 | 0.654394 | 0.764747 | 0.577406 |

Nguồn: reports/aspect_classifier/validation_comparison.csv. Loại: MEASURED.

## Chương 23 Metrics nhiều nhãn

Micro precision/recall cộng TP, FP, FN trên mọi cặp mẫu–aspect. Macro-F1 tính F1 từng aspect rồi trung bình, nên nhãn hiếm và zero support ảnh hưởng rõ. Exact match yêu cầu toàn bộ tập nhãn predicted giống gold của một mẫu.

EXAMPLE: gold={food,service}, predicted={food}; food đóng góp TP, service đóng góp FN, exact match của mẫu bằng 0. PROJECT RESULT: test micro-F1=0,832277; macro-F1=0,633628; exact match=0,726474; trung bình 1,063990 nhãn dự đoán/mẫu. Ba chỉ số đo những điều khác nhau nên không chọn một số rồi gọi chung là accuracy aspect.
Nguồn: src/foody/aspect.py::scores; reports/aspect_classifier/test_metrics.json.

## Chương 24 Đọc kết quả từng aspect

Bảng per-aspect bên dưới cho thấy food, service, price có support lớn hơn các aspect hiếm. Food F1=0,877193 với 347 positives; service=0,814570 với 159; price=0,842105 với 139. Đây là số positive labels trên 797 grouped texts, không phải 887 sentiment rows.

amenities và room có test support=0, F1=0 do zero_division=0 và vẫn nằm trong macro tất cả chín nhãn. Không có evidence về năng lực phát hiện hai lớp này trên test; cũng không được tự bỏ chúng để cải thiện macro-F1 công bố. Chỉ có thể thêm một phép phân tích hỗ trợ với mẫu số nói rõ, giữ metric gốc.
Nguồn: reports/aspect_classifier/test_per_aspect.csv; src/foody/aspect.py.

Bảng 16. Aspect test per label

| Aspect | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- |
| ambiance | 0.774194 | 0.676056 | 0.721805 | 71 |
| amenities | 0 | 0 | 0 | 0 |
| cleanliness | 1 | 0.793103 | 0.884615 | 29 |
| food | 0.890208 | 0.864553 | 0.877193 | 347 |
| location | 0.750000 | 0.840000 | 0.792453 | 25 |
| overall | 0.798165 | 0.743590 | 0.769912 | 117 |
| price | 0.821918 | 0.863309 | 0.842105 | 139 |
| room | 0 | 0 | 0 | 0 |
| service | 0.860140 | 0.773585 | 0.814570 | 159 |

Nguồn: reports/aspect_classifier/test_per_aspect.csv. Loại: MEASURED.

![F1 và support từng aspect](../reports/task2/figures/aspect_per_class_f1.png)

Hình 6. F1 và support từng aspect. Nguồn: reports/task2/figures/aspect_per_class_f1.png. Không đánh giá năng lực amenities/room khi support=0.

## Chương 25 Issue extraction là heuristic

extract_issues chỉ xét text khi overall predicted sentiment là negative và aspect tương ứng được dự đoán. Các cụm hẹp như “không ngon”, “phục vụ chậm”, “đợi lâu”, “giá cao”, “bất lịch sự” ánh xạ sang food_taste, slow_service, waiting_time, expensive, staff_attitude. Mỗi kết quả là tập unique issue names.

Code kiểm tra phủ định ngay trước cụm để tránh “không đắt” thành expensive. Nó không hiểu mọi sarcasm hoặc mixed sentiment; negative tổng thể có thể bỏ sót phàn nàn cục bộ trong review nhìn chung positive. Method được gắn heuristic_v1, không có supervised issue accuracy. Người bảo vệ nên gọi đây là tín hiệu hỗ trợ đọc review, không phải ground-truth complaint mining.
Nguồn: src/foody/enrichment.py::ISSUE_RULES, extract_issues; reports/foody_intelligence/issue_rules.json.

## Chương 26 RAG từ đầu

LLM có thể sinh câu nghe hợp lý nhưng không có căn cứ trong dữ liệu nhà hàng. Retrieval-Augmented Generation đưa các review được tìm thấy vào prompt để câu trả lời có nguồn. Retrieval là tìm tài liệu; generation là viết lời đáp; validator kiểm tra output có bám nguồn không. Ba thành phần có failure mode khác nhau.

EXAMPLE: hỏi “Nhân viên phục vụ có vấn đề gì không?” tại Hanuri. Hệ thống cần review về service và đúng chiều phàn nàn; review chỉ khen giá rẻ không đủ trả lời. Không thấy bằng chứng phù hợp thì trả insufficient evidence. Có bằng chứng nhưng Qwen viết sai thì dùng extractive fallback. RAG không biến một vài review thành thống kê đại diện về toàn bộ khách hàng.
Nguồn: src/rag_v3/service.py; src/rag_v3/evidence.py; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 27 Document chunk và token

Document là đơn vị nội dung có định danh và metadata; chunk là phần được cắt từ một document; token là đơn vị tokenizer mã hóa, có thể nhỏ hơn một từ tiếng Việt. Đếm ký tự hoặc từ không thay thế được token accounting. Cùng text, tokenizer MiniLM và Qwen có thể cho số token khác nhau.

Chunk size C giới hạn số token; overlap O lặp phần giáp ranh để giữ liên tục; stride S=C−O là bước dịch. Chunk nhỏ giảm nội dung thừa nhưng có thể cắt mất quan hệ phủ định hoặc ngữ cảnh. Chunk lớn giữ nhiều nghĩa hơn nhưng tăng chi phí và có nguy cơ bị truncation. Overlap tăng số token lưu/nhúng và đòi hỏi dedup khi tổng hợp evidence.
Nguồn: scripts/task2_rag_accounting.py; reports/task2/CHUNKING_DECISION.md.

## Chương 28 Công thức số chunk

THEORY: với T>0, 0≤O<C, N=max(1, ceil((T−C)/(C−O))+1). Hàm max giữ ít nhất một chunk với văn bản ngắn; biểu thức ceiling đảm bảo phần đuôi không bị bỏ. Trong script, policy_measure thực hiện chia chỉ bên trong từng review.

EXAMPLE — không phải số liệu project: T=900, C=256, O=32. S=224; (900−256)/224=2,875; ceil=3; N=4. Tổng vị trí token qua các chunk là T+(N−1)×O=996 nếu cửa sổ cuối được cắt đúng tại cuối text. Phải tính trên từng review rồi cộng, không nối 32.457 review thành một chuỗi lớn.
Nguồn: scripts/task2_rag_accounting.py; phụ lục công thức của tài liệu này.

## Chương 29 Chính sách một review một document

prepare_rag lọc valid_for_ai có prediction và drop_duplicates(review_id), tạo JSONL với id, text, metadata. Index được chấp nhận chứa 32.457 document và vector tương ứng. Chính sách này giúp review_id–citation và filter restaurant nhất quán, không gộp review của nhà hàng khác.

Giới hạn quan trọng: MiniLM runtime được ghi nhận truncation 128 token. Có 11.235 review, tức 34,615029%, dài hơn 128 content tokens; phần đuôi có thể không ảnh hưởng embedding dù BM25 và evidence còn full text. Mean=115,550297, median=92, p95=288, max=2.124 token. 2.239 review vượt 256 và 222 vượt 512.

Không chọn 128/256/512 cho index mới trong task này vì chỉ có simulation workload, chưa có đánh giá retrieval của các index thay thế. Giữ index đã nghiệm thu là quyết định về tính nhất quán artifact, không chứng minh one-review là tối ưu về chất lượng.
Nguồn: src/foody/pipeline.py::prepare_rag; reports/task2/rag_token_statistics.json; reports/task2/chunking_comparison.csv.

## Chương 30 So sánh chính sách chunk

Bảy policy được mô phỏng trên độ dài token thực, giữ ranh giới review và metadata. 128/0 tạo 46.968 chunks; 128/32 tạo 49.063; 256/0 tạo 34.962; 256/32 tạo 35.057; 512/0 tạo 32.688; 512/64 tạo 32.692. Overlap tăng workload nhưng không tạo thêm review gốc.

Thời gian thay thế được ước lượng bằng chunk_count / throughput đã đo. Không có embedding hoặc retrieval chạy lại trong các dòng simulation. Bảng dùng chữ DERIVED cho số chunk và estimated_seconds; thời gian index gốc là MEASURED. Khi đổi policy thật phải bổ sung chunk_id, aggregation về review_id và bộ relevance để đánh giá.
Nguồn: reports/task2/chunking_comparison.csv; reports/task2/embedding_workload.csv.

Bảng 17. Simulation chunk workload

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

Bảng 18. Mean content tokens mỗi chunk theo simulation

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

## Chương 31 Token accounting

scripts/task2_rag_accounting.py nạp tokenizer JSON local, gọi no_padding và no_truncation để đếm content tokens không gồm special tokens. T_total là tổng độ dài; T_avg=T_total/N. Histogram cho phép tính lại median/percentile và số review vượt threshold mà không tokenize hay index lại.

PROJECT RESULT: MiniLM có 3.750.416 tokens, Qwen2.5 có 4.105.360 tokens trên cùng 32.457 review. Hai tổng thuộc hai vocabulary, không được cộng thành số billable duy nhất. Token của corpus cũng khác token request: request còn system instruction, question, chat template, selected evidence và retries.
Nguồn: reports/task2/rag_token_statistics.json; reports/task2/rag_token_distribution.csv; scripts/task2_rag_accounting.py.

Bảng 19. Token statistics không truncation

| Tokenizer | Total | Mean | Median | p95 | Max |
| --- | --- | --- | --- | --- | --- |
| minilm_embedding | 3750416 | 115.550297 | 92.000000 | 288.000000 | 2124 |
| qwen2_5_3b_generation | 4105360 | 126.486120 | 101.000000 | 315.000000 | 2249 |

Nguồn: reports/task2/rag_token_statistics.json. Loại: MEASURED.

![Phân bố token trên corpus Foody](../reports/task2/rag_token_distribution.png)

Hình 7. Phân bố token trên corpus Foody. Nguồn: reports/task2/rag_token_distribution.png.

## Chương 32 Embedding và MiniLM

Embedding ánh xạ text sang vector số để so sánh gần nhau theo biểu diễn học được. EXAMPLE: “phục vụ chậm” và “đem món quá lâu” có thể gần nhau hơn hai câu không liên quan; đó là minh họa ý nghĩa semantic, không phải điểm similarity đã đo của project.

Model được chọn là sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, dùng bản ONNX của Qdrant qua FastEmbed trên CPU. LocalEmbeddings chuẩn hóa vector L2 và kiểm tra dimension=384. 384 là kích thước kiến trúc model, không phải hyperparameter nhóm tune từ 128 lên 384. Repository không dùng SentenceTransformer trực tiếp cho runtime hiện hành dù tên model thuộc họ Sentence Transformers.

Dense similarity không bảo đảm cùng chiều sentiment hoặc đúng issue. Hai câu “dịch vụ rất tốt” và “dịch vụ rất tệ” có thể cùng chủ đề; vì vậy V3 thêm filter và compatibility rules.
Nguồn: src/rag/embeddings.py; reports/rag/embedding_selection.json; model card Sentence Transformers.

## Chương 33 Tính bộ nhớ vector

DERIVED: 32.457 × 384 × 4 = 49.853.952 bytes = 49,853952 MB = 47,544434 MiB cho payload float32. MB chia 10⁶; MiB chia 2²⁰. Con số này không phải RAM tối đa hoặc dung lượng thư mục Chroma.

Chroma còn metadata, text, HNSW, SQLite và overhead; model ONNX và runtime cũng chiếm RAM riêng. Không cộng model disk size với raw vector estimate rồi gọi đó là VRAM. Appendix cung cấp phép tính chính xác bằng Python và nguồn N,d,dtype.
Nguồn: data/foody/vector_store/index_manifest.json; src/rag/embeddings.py::_embed.

## Chương 34 Chọn embedding bằng evidence

Có một so sánh nhỏ thật, không phải không có benchmark. Pool 612 documents gồm 600 mẫu ngẫu nhiên và known-positive IDs, sáu câu hỏi. Potion multilingual 256 chiều có known-positive recall@10=0,166667, MRR=0,104167; MiniLM 384 chiều có 0,333333 và 0,333333. Quy tắc chọn recall@10 rồi MRR rồi query time chọn MiniLM.

Potion nhanh hơn nhiều trong đo pool nhưng chất lượng theo nhãn dương đã biết thấp hơn. Pool nhỏ và labels chưa đầy đủ; không có exhaustive embedding model benchmark. Chọn MiniLM trong hai ứng viên không chứng minh thắng mọi encoder hoặc tối ưu với full index. Full-index metric giảm so với pool là điều cần giải thích vì không gian cạnh tranh tăng.
Nguồn: src/rag/evaluation.py::compare_candidates; reports/rag/embedding_comparison.csv.

Bảng 20. Embedding selection pool612

| Model | Dim | KP recall10 | MRR | Query embed ms |
| --- | --- | --- | --- | --- |
| minishlab/potion-multilingual-128M | 256 | 0.166667 | 0.104167 | 0.223617 |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | 0.333333 | 0.333333 | 3.209650 |

Nguồn: reports/rag/embedding_comparison.csv. Loại: MEASURED.

## Chương 35 Chroma và metadata filtering

Chroma lưu collection persistent với cosine HNSW. id của vector bằng review_id; metadata gồm restaurant_key/name, timestamp, raw_rating, predicted_sentiment, aspects/issues dạng JSON và Boolean aspect_<name>. open_collection kiểm tra count bằng manifest trước khi dùng.

Filter giới hạn tập ứng viên đúng nhà hàng, khoảng ngày hoặc nhãn dự đoán. Chroma score là độ gần trong không gian embedding, không phải xác suất câu trả lời đúng. timestamp_epoch được code dùng cho thứ tự và filter từ timestamp local naive; không phải chứng cứ thời điểm UTC đã được xác nhận. Manifest cố định model hash và document hash để phát hiện mismatch.
Nguồn: src/rag/vector_store.py; src/rag/retriever.py; reports/task2/RAG_METADATA_SCHEMA.md.

## Chương 36 BM25 và implementation SQLite

BM25 đánh giá mức phù hợp từ khóa bằng tần suất, độ hiếm của term và chuẩn hóa độ dài document. k1 điều khiển saturation của tần suất; b điều chỉnh tác động độ dài so với avgdl. Công thức tổng quát có trong phụ lục; áp dụng cụ thể còn phụ thuộc tokenizer và IDF của thư viện.

PROJECT CONFIG: src/rag_v2/lexical.py gọi bm25(reviews_fts) của SQLite FTS5, dùng unicode61 remove_diacritics 2. Code không tune k1/b; tài liệu SQLite ghi cố định k1=1,2 và b=0,75 cho hàm này. SQLite trả số âm để rank nhỏ hơn tốt hơn; code đảo dấu khi tạo ReviewHit.score. FTS query ghép unigram/bigram/trigram bằng OR, quote token và bind SQL parameters.

BM25 có thể bắt tốt cụm chê rõ ràng nhưng yếu với diễn đạt không chia sẻ từ. Bỏ dấu và stopwords ảnh hưởng matching; riêng từ “không” nằm trong stopwords unigram, trong khi phrase expression vẫn có thể chứa nó. Không mô tả BM25 như mô hình hiểu phủ định hoàn chỉnh.
Nguồn: src/rag_v2/lexical.py; SQLite FTS5 bm25 documentation.

## Chương 37 Dense retrieval và lexical retrieval

Dense tìm theo vector semantic, BM25 tìm theo token/phrase. Dense hữu ích với paraphrase; BM25 có lợi khi câu hỏi và review chia sẻ cụm cụ thể. Cả hai có thể tìm sai polarity, nhà hàng hoặc thời điểm nếu thiếu filter.

V1 dense trong benchmark full index có known-positive recall@5 bằng 0; BM25 tìm thêm known positive. Đây là quan sát trên sáu câu, không phải bằng chứng dense luôn kém BM25. Cách kết hợp RRF tránh cộng trực tiếp cosine với BM25 vốn khác scale, nhưng vẫn cần kiểm tra evidence vì fusion chỉ đổi xếp hạng.
Nguồn: src/rag_v2/hybrid.py; reports/rag_v3/retrieval_policies.csv.

## Chương 38 Reciprocal Rank Fusion

RRF(d)=Σ_r 1/(k+rank_r(d)); mỗi retriever góp một số theo thứ hạng, không dùng trực tiếp score của nó. rrf_fuse dùng k=60, rank bắt đầu từ 1, gộp theo review_id và tie-break theo ID. Candidate dense_top_n và lexical_top_n đều 20 trước lấy final top-k.

EXAMPLE: document A rank 1 và 4 có score 1/61+1/64≈0,032018; B rank 2 và 2 có 2/62≈0,032258. B nhỉnh hơn vì xuất hiện tốt ở cả hai. Đây là số minh họa, không phải retrieval score lưu của Hanuri.

Tăng k làm khác biệt giữa các thứ hạng đầu nhỏ hơn; giảm k ưu tiên top ranks mạnh hơn. k=60 và candidate pool 20 là engineering choices; chưa có sweep riêng chứng minh tối ưu.
Nguồn: src/rag_v2/hybrid.py::rrf_fuse, RetrievalConfig.

## Chương 39 RAG V1 và giới hạn dense only

V1 dùng selected MiniLM và Chroma full index. Trong shared V3 policy run, recall trên known-positive tại 5=0, tại 10=0,083333, MRR=0,018519, mean retrieval=16,519117 ms. Các số này phải ghi đúng run; bảng V2 candidate có mean 15,761 ms là một lần đo khác.

Một lỗi chính là gần chủ đề nhưng sai bằng chứng: review khen phục vụ không trả lời được câu hỏi phàn nàn service. Thêm LLM vào phía sau không thể bảo đảm sửa retrieval thiếu bằng chứng. V1 là historical experiment, không phải path Analyst đang dùng.
Nguồn: reports/rag_v3/retrieval_policies.csv; src/rag/service.py; reports/task2/RAG_ABLATION_FINAL.md.

Bảng 21. Retrieval policy measurements

| policy | known_hit_at_5 | known_hit_at_10 | known_mrr | mean_latency_ms | p95_latency_ms |
| --- | --- | --- | --- | --- | --- |
| RAG_V2_BM25 | 0.083333 | 0.083333 | 0.166667 | 240.010817 | 620.717600 |
| RAG_V1_DENSE | 0 | 0.083333 | 0.018519 | 16.519117 | 21.181625 |
| RAG_V2_RRF | 0.083333 | 0.083333 | 0.041667 | 120.094883 | 162.247875 |
| RAG_V2_EVIDENCE_RERANK | 0.083333 | 0.083333 | 0.055556 | 600.290550 | 1742.720075 |
| RAG_V3_ROUTED | 0.083333 | 0.083333 | 0.166667 | 140.970200 | 195.149225 |

Nguồn: reports/rag_v3/retrieval_policies.csv. Loại: MEASURED.

Chú thích: các cột known_hit lưu macro known-positive recall theo known_positive_scores; không phải binary Hit. Không gộp latency giữa hai run.

## Chương 40 RAG V2 và hybrid candidates

V2 thử dense, BM25, RRF, RRF+expansion và evidence reranking. Expansion thêm các term theo intent đã giới hạn; auto_filter có thể thêm negative và aspect khi câu hỏi là complaint. Rerank cộng hoặc trừ các trọng số nhỏ dựa trên aspect, compatibility và issue matches, không phải neural cross-encoder.

Trong V2 candidate run, BM25 MRR=0,166667; RRF=0,041667; expansion và rerank=0,055556. Thêm complexity không tăng Hit/known-positive coverage ở tập nhỏ. Rerank cần khoảng 313,404 ms trong run đó; shared V3 run ghi 600,291 ms cho policy V2, không nên so như paired speedup.

V2 đã tìm được evidence food nhưng một câu trả lời bị loại do không đúng topic, rồi trả insufficient. V3 thêm extractive fallback để giữ được thông tin có căn cứ. Không thể tái dựng mọi lỗi JSON V2 vì raw rejected generations cũ chưa được lưu đầy đủ.
Nguồn: src/rag_v2/hybrid.py; src/rag_v2/service.py; reports/rag_v2/retrieval_candidates.csv.

Bảng 22. Retrieval policy measurements

| mean_latency_ms | p95_latency_ms |
| --- | --- |
| 15.760817 | 18.318675 |
| 135.940683 | 188.461625 |
| 134.743750 | 182.257725 |
| 330.792183 | 419.118525 |
| 313.403533 | 398.832400 |

Nguồn: reports/rag_v2/retrieval_candidates.csv. Loại: MEASURED.

Chú thích: các cột known_hit lưu macro known-positive recall theo known_positive_scores; không phải binary Hit. Không gộp latency giữa hai run.

## Chương 41 RAG V3 và vai trò từng bước

route_query nhận dạng causal, complaint có aspect, general aspect hoặc summary. Complaint có aspect đi filtered BM25 kèm evidence rerank; general đi hybrid RRF. TREND_CAUSATION đi MART_TREND_GUARD và search_debug trả danh sách rỗng để không suy diễn nguyên nhân từ vài review. Tên guard không có nghĩa query handler luôn chạy một phép phân tích nhân quả trên mart.

build_packet giữ evidence hợp intent/polarity/topic, dedup text và lấy tối đa ba review. Qwen chỉ nhận packet này. attach_citation có thể gắn placeholder bằng overlap khi thiếu inline citation, nhưng sau đó vẫn phải qua validator. Tối đa hai lần sinh; không qua thì extractive_answer, không có evidence thì insufficient.

RRF không áp dụng mọi query; BM25 complaint route tắt dense. Evidence rules và clause validator là deterministic heuristic, chưa phải human entailment oracle. Code hiện tại và các ca nghiệm thu là phạm vi lời khẳng định “đã chấp nhận”.
Nguồn: src/rag_v3/routing.py; src/rag_v3/retriever.py; src/rag_v3/evidence.py; src/rag_v3/service.py.

![Observed retrieval và safety progression](../reports/task2/figures/rag_ablation_final.png)

Hình 8. Observed retrieval và safety progression. Nguồn: reports/task2/figures/rag_ablation_final.png. Nhãn Hit của hình gốc đọc như known-positive recall; không phải causal component-off ablation.

## Chương 42 Hit at k và sai lệch tên cột trong báo cáo cũ

THEORY: Hit@k(q)=1 nếu top-k có ít nhất một relevant document, ngược lại 0; mean Hit@k lấy trung bình trên query. EXAMPLE: ba query có hit [1,0,1] thì Hit@k=2/3. Đây là chỉ số có hoặc không có, không chia số hit cho số gold của từng query.

AUDIT: known_positive_scores trong src/rag/evaluation.py thực sự tính |top-k ∩ known positives|/|known positives|. scripts/evaluate_rag_v3_retrieval.py đổi tên trung bình này thành known_hit_at_5/10. Vì vậy giá trị 0,083333 đã công bố phải được mô tả là macro known-positive recall, không phải binary Hit@k. Tài liệu giữ nguyên số và nêu tên cột lịch sử để truy vết, không sửa experiment.
Nguồn: src/rag/evaluation.py::known_positive_scores; scripts/evaluate_rag_v3_retrieval.py; reports/rag_v3/retrieval_policy_rows.csv.

## Chương 43 Mean Reciprocal Rank

MRR nhìn vị trí relevant đầu tiên: query có rank r góp 1/r, không tìm thấy góp 0. MRR là trung bình qua mọi query. EXAMPLE: ranks 1,4,missing cho (1+0,25+0)/3=0,416667. MRR không biết có bao nhiêu relevant khác phía sau.

PROJECT RESULT: V3 routed MRR known-positive=0,166667 trên sáu câu, tức tổng reciprocal ranks bằng 1. Điều này không có nghĩa 16,7% review corpus liên quan. Cần đọc query rows và tập known positives chưa đầy đủ để hiểu rank; reviewer chưa gán nhãn cho mọi tài liệu.
Nguồn: src/rag/evaluation.py; reports/rag_v3/retrieval_policy_rows.csv.

## Chương 44 Recall at k và nhãn relevance chưa đầy đủ

Recall@k(q)=số relevant retrieved trong top-k / tổng số relevant của query. Full recall đòi hỏi biết đầy đủ tập relevant. Project chỉ có các known-positive IDs do người xây benchmark chọn, vì vậy các số recall trong tài liệu này đều ghi rõ known-positive, không phải full-corpus recall hoặc accuracy của search.

Một tài liệu không nằm trong known positives có thể vẫn thực sự liên quan. Vì thế low known-positive score không chứng minh mọi retrieved review đều sai, còn số cao cũng không chứng minh answer grounded. Context precision, context recall chuẩn hóa và đánh giá người dùng đầy đủ chưa có trong evidence này.
Nguồn: reports/rag/development_judgments.json; reports/rag/rag_metrics.json; src/rag/evaluation.py.

## Chương 45 Evidence packet và citation

Packet chứa question_intent, aspect, restaurant, evidence và aggregates. Mỗi evidence có ref E1/E2/E3, review_id thật, sentiment/aspects/issues dự đoán, rating và đoạn text giới hạn. Payload generation dùng placeholder ngắn để giảm khả năng model viết sai một ID dài; response cuối map lại ID chính xác.

frequency_supported=False ngăn suy ra “đa số”, “thường xuyên” từ vài review đã chọn. accepted_review_count đếm evidence sau gate, không phải tổng review của nhà hàng. _packet_text thường lấy 350 ký tự hoặc đoạn quanh complaint cue; đây là truncation bằng ký tự ở packet, khác giới hạn token của embedding.
Nguồn: src/rag_v3/evidence.py::Packet, build_packet, _packet_text, evidence_for_refs.

## Chương 46 Support validator và giới hạn heuristic

validate_packet_citations kiểm tra inline refs, danh sách refs, aspect/topic, polarity, số ít/số nhiều, frequency language và mixed evidence. Sau đó tách câu/mệnh đề, yêu cầu citation cho từng assertion và overlap với chính review được dẫn. _clause_supported còn kiểm tra các cue issue, polarity staff attitude và loại numeric claims được sinh.

Một câu có review ID đúng vẫn có thể chứa claim không có trong review. Do đó schema và citation validity chưa đủ. Tuy vậy overlap/cue rule cũng có thể bỏ sót hoặc loại nhầm paraphrase; số unsupported accepted bằng 0 là “validator không phát hiện” trong sáu ca, không phải chứng minh không hallucinate trên mọi đầu vào.
Nguồn: src/rag_v3/evidence.py::validate_packet_citations, _clause_supported; reports/rag_v3/generation_failure_analysis.json.

## Chương 47 Fallback và từ chối khi thiếu bằng chứng

Khi có packet hợp lệ nhưng hai lần sinh không qua, extractive_answer chọn evidence đầu, trích tối đa khoảng 180 ký tự và gắn ref. Mode=extractive_fallback hiển thị cho người dùng. Đây là cơ chế bảo toàn evidence, nhưng answer có thể chưa đủ để trả lời câu hỏi “phổ biến nhất”.

Khi packet rỗng hoặc query causal bị guard, không gọi generation để cố tạo lời giải thích. Trả insufficient-evidence là hành vi đúng cho ba ca thiếu bằng chứng trong nghiệm thu. Fallback không phải crash, nhưng fallback nhiều vẫn cho thấy giới hạn generator; không dùng tỷ lệ answer hợp lệ sau fallback để quảng cáo khả năng synthesis thuần của LLM.
Nguồn: src/rag_v3/service.py::answer_question_v3; src/rag_v3/evidence.py::extractive_answer.

## Chương 48 Qwen 1 phẩy 5B và 3B

B biểu thị tỷ tham số xấp xỉ, không phải dung lượng GB. Qwen 1,5B là model sentiment V1/V2 và cấu hình gateway mặc định lịch sử; accepted Streamlit V3 chọn Qwen 3B qua config/demo.yaml. Compose cũng mặc định file 3B, cho phép override rõ ràng bằng QWEN_MODEL_FILE.

Trong accepted replay sáu ca, cả hai model có 2 supported complete, 1 supported incomplete, 3 correct insufficient và 0 validator-detected unsupported accepted; fallback giảm từ 3 xuống 2 với 3B. Đây là tín hiệu demo nhỏ để chọn 3B, không phải general LLM ranking. Model file 3B=2.104,932768 MB và 1,5B=1.117,320736 MB; RAM/VRAM còn runtime và context overhead.
Nguồn: config/demo.yaml; qwen_v1.yaml; qwen_v3_3b.yaml; reports/rag_v3/generation_metrics.json; reports/task2/FEASIBILITY.csv.

## Chương 49 Benchmark Qwen Llama DeepSeek

Ba model dùng cùng sáu saved evidence packets, prompt V3, llama.cpp b11429, temperature=0, seed=42, cap 128 output tokens, không rerun retrieval. Qwen2.5 3B và Llama-3.2 3B so với DeepSeek-R1-Distill-Qwen 1,5B. DeepSeek distill có gốc Qwen; gọi là ba nhãn họ sản phẩm không có nghĩa ba kiến trúc base độc lập cùng kích thước.

Final gate giữ cùng 2 complete, 1 incomplete, 3 insufficient ở cả ba; Qwen replay mới fallback 3, Llama 2, DeepSeek 3. DeepSeek không tạo schema parseable trong các ca answerable dưới protocol này; không kết luận model nói chung yếu. Qwen replay mới bị contention và chậm hơn accepted replay, nên không trộn hai lần đo.

Token response của lỗi timeout/parse thiếu phải để N/A. DeepSeek server-log counters 4.228 input và 768 output trên sáu attempts là nguồn đo khác, không điền vào cột successful-response usage. Ollama và llama.cpp là runtime, không phải model; benchmark thực tế này dùng llama.cpp.
Nguồn: reports/task2/llm_comparison.csv; reports/task2/llm_benchmark_provenance.json; reports/task2/LLM_BENCHMARK.md.

Bảng 23. Ba LLM trên fixed packets

| Family | Size MB | Valid schema | Applicable | Fallback | Usage unknown |
| --- | --- | --- | --- | --- | --- |
| Qwen | 2104.932768 | 1 | 3 | 3 | 2 |
| Llama | 2019.377696 | 1 | 3 | 2 | 2 |
| DeepSeek | 1117.320800 | 0 | 3 | 3 | 3 |

Nguồn: reports/task2/llm_comparison.csv. Loại: MEASURED.

Bảng 24. Token và latency theo scope

| Family | Known input | Known output | Active gen ms | Answerable wall ms |
| --- | --- | --- | --- | --- |
| Qwen | 964 | 56 | 112434.980700 | 197793.861933 |
| Llama | 469 | 22 | 61069.005000 | 180586.199733 |
| DeepSeek | N/A | N/A | N/A | 4788.397000 |

Nguồn: reports/task2/llm_comparison.csv. Loại: MEASURED.

![Three family generator smoke](../reports/task2/figures/three_llm_comparison.png)

Hình 9. Three family generator smoke. Nguồn: reports/task2/figures/three_llm_comparison.png. Khác parameter scale và resource contention; không general ranking.

## Chương 50 Latency mean p95 và phạm vi đo

Mean là tổng latency chia số quan sát; p95 là percentile 95, phản ánh phần đuôi chậm. Với numpy/pandas mặc định linear interpolation, p95 có thể nằm giữa hai mẫu. Chỉ sáu query thì percentile rất nhạy; không dùng nó như SLA ổn định cho người dùng thật.

Retrieval latency đo tìm ứng viên; generation latency đo các call hoàn thành; end-to-end gồm retrieval, gate, retries/fallback và overhead. Telemetry cộng usages chỉ của attempts có usage trả về, nên không luôn chứa thời gian timeout. Benchmark còn cột answerable wall time để phản ánh toàn bộ chờ ở các câu có evidence. Mean toàn sáu ca chứa ba refusal nhanh khác mean ba answerable.
Nguồn: src/rag_v3/service.py; scripts/task2_llm_benchmark.py; reports/task2/FEASIBILITY.csv.

## Chương 51 Disk size RAM VRAM và quantization

Model_size_bytes là kích thước file weights trên đĩa; RSS là bộ nhớ resident của process; VRAM là bộ nhớ GPU. Sampling GPU toàn hệ thống có thể gồm ứng dụng khác và không chứng minh process inference dùng hết lượng đó. Context/KV cache, batch và runtime tạo overhead ngoài weights.

Q4_K_M giảm biểu diễn weights để model chạy trên máy cá nhân, có thể đổi quality. Repository không có đối chứng full precision để tính mất mát do quantization. V1 mất sampler evaluation, chỉ có idle probe riêng; three-family benchmark có sampled RSS nhưng GPU số đo system-wide. Docker nghiệm thu chạy CPU, GPU container NOT VERIFIED dù lệnh yêu cầu gpu layers=99.
Nguồn: reports/proposed_v1/qwen_resource_report.json; reports/task2/llm_comparison.csv; reports/task2/DOCKER_ACCEPTANCE.md.

Bảng 25. Feasibility theo từng task

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

Hình 10. Latency và kích thước artifact. Nguồn: reports/task2/figures/latency_model_size.png. Các task/run khác nhau; DeepSeek dùng answerable wall khi active generation không có.

## Chương 52 MLOps và LLMOps

MLOps quản lý data/model version, training evaluation, reproducibility và phục vụ. MLflow lưu tham số, metrics, artifact của nghiên cứu; DVC mô tả phụ thuộc/stage. LLMOps còn cần model/prompt version, token, latency, schema, citations và cách đáp hoặc fallback. Project không đăng ký một production LLM mới.

record ghi SQLite state/llmops.sqlite với component, timestamp, model hash, prompt version, rag_version, retrieval_method, query_route, evidence_count, support_gate_status, clause_support_status, tokens và latency. safe_filters chỉ giữ restaurant_key, ngày, sentiment, aspect. Không lưu raw question/review trong operational event; intentional evaluation audit riêng có thể lưu raw generation nên không đồng nhất hai nơi.

Theo dõi mode và failure category giúp phát hiện model đang fallback nhiều dù HTTP vẫn 200. Health endpoint chỉ trả lời khả năng truy cập cơ bản, không thay thế quality monitoring.
Nguồn: src/rag/monitoring.py; src/ml/mlflow_tracking.py; src/rag_v3/service.py.

## Chương 53 Bốn trang Streamlit

Restaurant Intelligence đọc marts, chọn nhà hàng/ngày, hiển thị rating, sentiment, aspect/issues và historical alerts; nút health report gọi V3 health service. Review Explorer đọc enriched reviews, lọc và phân biệt trường raw với predicted. AI Review Analyst nhận question/restaurant/filter, gọi RoutedRetriever và selected_v3_gateway trực tiếp trong process Streamlit, rồi hiển thị answer, evidence và mode.

LLMOps Monitor đọc events và report, tách số liệu nghiên cứu với inference demo. Dữ liệu đọc được cache bằng st.cache_data; cache không train lại model. Exception được hiển thị thành trạng thái RAG unavailable để frontend còn đọc dashboard. Đường Analyst hiện tại không gửi HTTP sang rag-backend; sơ đồ chuỗi Streamlit→FastAPI→Qwen sẽ mô tả sai source.
Nguồn: app/app.py::restaurant_page, explorer_page, analyst_page, monitor_page.

## Chương 54 FastAPI và HTTP

API định nghĩa hợp đồng request/response qua HTTP. FastAPI ở app/api.py có GET /health, POST /ask và GET /restaurants/{restaurant}/health-report. Docker expose host port 8000; Streamlit là frontend ở 8501. HTTP 200 nghĩa endpoint xử lý được, không tự chứng minh một truy vấn RAG V3 đã chạy.

/ask hiện import src.rag.service.answer_question và LLMGateway mặc định lịch sử, không dùng answer_question_v3. /health kiểm tra index_manifest và file Qwen v1 1,5B, nên trường qwen_weights_available không phải xác minh model 3B đang serve. Accepted V3 query là đường Streamlit/CLI; tài liệu ghi rõ API là service bổ sung với path legacy, không sửa source trong task documentation.
Nguồn: app/api.py; docker-compose.yml; reports/task2/MICROSERVICE_ARCHITECTURE.md.

## Chương 55 Docker từ đầu

Docker đóng gói chương trình và dependency thành image. Dockerfile là công thức build; container là một instance của image đang chạy hoặc đã kết thúc. Volume/bind mount đưa dữ liệu ngoài image vào container. Network cho service giao tiếp; port mapping đưa cổng container ra host; environment variable thay cấu hình tại runtime.

Compose gom khai báo service, build, command, ports, mounts và profile trong YAML. Dockerfile.rag dùng Python 3.12 và requirements-demo.txt cho Streamlit/FastAPI; Dockerfile lịch sử dùng Python 3.11 và requirements.txt cho pipeline CLI. Images không mang data/models private; chạy được demo cần mounts có artifact đúng hash.
Nguồn: Dockerfile; Dockerfile.rag; docker-compose.yml.

## Chương 56 Image và container

Có thể hình dung image như bản mẫu đã đóng gói và container như một phiên thực thi từ bản mẫu đó. Cùng application image có thể chạy lệnh Streamlit hoặc uvicorn trong hai container khác nhau. Thay requirements trên host không tự sửa filesystem bên trong image đã build; phải rebuild rồi recreate service.

Container lưu writable layer riêng nhưng dữ liệu bind mount nằm trên host. Xóa container không đồng nghĩa xóa source artifact được mount; ngược lại ghi vào mount RW có thể thay file host. Vì vậy model/report mount dùng ro trong serving path; data/state vẫn có quyền ghi theo Compose hiện tại.
Nguồn: docker-compose.yml; Dockerfile.rag; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 57 Các service Docker thực tế

Default services: pipeline chạy CLI help một lần; qwen chạy llama-server; rag-backend chạy FastAPI; streamlit chạy giao diện. prefect-server và scheduler nằm trong profile orchestration, không bật mặc định và không bắt buộc cho acceptance hiện tại.

Luồng đúng theo source: Browser → Streamlit :8501 → module RAG V3 trong container Streamlit → Qwen :8193; module đọc Chroma/BM25 qua data mount và ghi state SQLite. rag-backend :8000 là service song song có API legacy. Qwen local launcher dùng :8194; QWEN_BASE_URL=http://qwen:8193 trong Compose override URL kết nối.

Không gọi retrieval, validator hoặc monitoring là container độc lập: chúng là Python modules. Sơ đồ kiến trúc cần thể hiện ranh giới process để không phóng đại microservices.
Nguồn: app/app.py; app/api.py; src/llm/gateway.py; docker-compose.yml.

Bảng 26. Service boundary thực tế

| Service | Role | Port / state | Scope |
| --- | --- | --- | --- |
| pipeline | CLI one-shot | exit0 | --help, không ingestion |
| qwen | llama-server 3B | 8193 healthy | CPU accepted; GPU chưa verified |
| rag-backend | FastAPI legacy | 8000 Up HTTP200 | Không phải V3 Analyst API |
| streamlit | UI + V3 modules | 8501 Up HTTP200 | Direct V3→Qwen |
| prefect-server/scheduler | orchestration profile | optional 4200 | Không bật mặc định |

Nguồn: docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md. Loại: CONFIGURED + MEASURED acceptance.

## Chương 58 Mount dữ liệu model state và reports

Serving containers mount ./data→/app/data RW, ./models→/app/models RO, ./state→/app/state RW và ./reports→/app/reports RO. Qwen mount ./models→/models RO. Pipeline lịch sử chỉ mount data/state/logs. Các đường container khác host Windows nhưng giữ relative project structure.

Không bake weights, review private và indexes vào image giúp giảm artifact build, tránh đưa data riêng lên GHCR và cho phép phục hồi đúng phiên bản ngoài image. Đổi file mount vẫn có thể gây hash mismatch; pin manifest và preflight cần thiết. RO là thuộc tính mount, không phải mã hóa hay cơ chế bảo vệ toàn host.
Nguồn: docker-compose.yml; .dockerignore; .gitignore; src/demo.py.

## Chương 59 Case study lỗi đường dẫn Windows và Linux

embedding_selection.json lưu model_file dạng models\embeddings\...\model_optimized.onnx. Linux Path không coi backslash là separator như Windows nên lookup nhắm vào một tên file chứa dấu backslash và gây FileNotFoundError dù file thật đã được mount.

selected_retriever thay separator khi đọc saved path rồi vẫn kiểm checksum model. Fix này không rebuild embedding hoặc đổi model. Bài học là artifact metadata có thể mang giả định hệ điều hành; mount đúng chưa đủ nếu serialized path sai. Báo cáo Docker giữ traceback và xác minh file readable để phân biệt nguyên nhân path với mất dữ liệu.
Nguồn: src/rag/cli.py::selected_retriever; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 60 Case study thiếu psutil trong pipeline

Traceback của pipeline là ModuleNotFoundError: No module named 'psutil'. src.cli import rag_v3.cli → llm.gateway → proposed_v1.runtime, nơi import psutil. Image pipeline cài requirements.txt, trong khi psutil đã có ở requirements-demo.txt; sửa file demo sẽ không sửa dependency của pipeline.

Fix đã chấp nhận thêm psutil==7.2.2 vào requirements.txt rồi docker compose build pipeline và up -d pipeline. Import probe tải được psutil và src.cli; lệnh --help hoàn tất exit 0. Không chạy ingestion để kiểm tra một lỗi xảy ra ngay lúc import. Task tài liệu này chỉ mô tả fix đã có.
Nguồn: requirements.txt; Dockerfile; src/proposed_v1/runtime.py; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 61 Đọc trạng thái Exited 0

Pipeline default command là python -m src.cli --help. Nó là one-shot: in usage rồi kết thúc. Exited (0) xác nhận hành vi này thành công; không cần giữ process bằng sleep để gọi healthy. Exit non-zero trước action mới là startup failure cần điều tra.

docker compose ps thường chỉ hiện service chạy; dùng ps -a để thấy one-shot đã hoàn tất. Qwen có Docker healthcheck thật; backend và Streamlit trong Compose hiện chưa có Docker healthcheck, nhưng HTTP health đã trả 200. Viết “Up và HTTP 200” chính xác hơn gán nhầm trạng thái Docker healthy cho cả ba.
Nguồn: Dockerfile; docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 62 YAML trong project

YAML biểu diễn key:value, list bằng dấu gạch đầu dòng hoặc ngoặc vuông, và nesting bằng indentation. .yml và .yaml chỉ là hai đuôi của cùng định dạng. Trong Compose, services là mapping; streamlit là key; build/context/dockerfile là các cấp con; ports và volumes là list. Không thay indentation bằng tab.

Các chuỗi ${QWEN_MODEL_FILE:-...} trong Compose là interpolation runtime; ${{ github.ref }} trong GitHub Actions là expression của workflow engine. Chúng không phải Python syntax. Một parser YAML generic có thể xử lý từ on khác kỳ vọng YAML 1.2; đọc workflow phải theo semantics của GitHub Actions, không suy kết quả chỉ từ một thư viện parse.
Nguồn: docker-compose.yml; .github/workflows/ci.yml; .github/workflows/release.yml.

```yaml
services:
  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.rag
    ports: ["8501:8501"]
```

Trích rút gọn từ docker-compose.yml: services chứa service streamlit; build.context là build context hiện tại; dockerfile chỉ image recipe; 8501 bên trái là host và bên phải là container. Các mounts/environment khác vẫn tồn tại trong file gốc.

## Chương 63 Git và lịch sử source

Repository lưu lịch sử snapshot theo commit. Branch main trỏ vào commit; remote origin là URL repository; fetch lấy remote refs; pull lấy và tích hợp; push gửi commit; tag đánh dấu một phiên bản. Rebase đặt lại các commit local lên base mới và đổi commit IDs, nên cần hiểu lịch sử trước khi dùng.

EXAMPLE minh họa: nếu README được sửa trên GitHub trong khi local có commit riêng, push có thể bị non-fast-forward. git fetch origin rồi xem log/diff, git pull --rebase origin main, giải quyết conflict, chạy kiểm tra và push lại có thể tích hợp an toàn. Không có log trong repo đủ chứng minh chuỗi push rejection cụ thể đã xảy ra; tài liệu không trình bày ví dụ này như sự kiện đã xác minh. Không cần force push để giải quyết trường hợp minh họa đó.

PROJECT VERIFIED: HEAD 4229a8b3998392c97f4b7a8c9e3795830285dbce, tag v1.0.1, cùng commit CI/release đã kiểm tra. Tài liệu mới tạo sau commit này nên chưa được bao phủ bởi run đó.
Nguồn: git log/tag tại audit; reports/task2/CICD_EVIDENCE.md; public GitHub Actions API.

## Chương 64 Continuous Integration và Delivery

CI tự động kiểm tra source mới để phát hiện lỗi trước khi tích hợp. CD ở project là build và publish application image lên GitHub Container Registry. Workflow không khai báo remote deployment environment, database migration hay rollout production; publish thành công không có nghĩa người dùng ngoài Internet đã truy cập ứng dụng.

Runtime acceptance local bổ sung phần CI artifact-free không kiểm: weights, Foody index, Qwen health, real query và LLMOps event. Hai nhóm evidence trả lời hai câu hỏi khác nhau: source/image có build được, và artifact-mounted demo có thực thi được.
Nguồn: .github/workflows/ci.yml; .github/workflows/release.yml; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 65 GitHub Actions từ workflow đến step

Workflow là file YAML mô tả tự động hóa. Trigger quyết định khi chạy; job chạy trên runner; step có thể là action uses hoặc lệnh run. checkout lấy source, setup-python chọn interpreter, cache pip giảm tải cài đặt. Secret/token cấp quyền cần thiết mà không hardcode vào source.

CI cấp contents:read; release thêm packages:write để publish GHCR bằng GITHUB_TOKEN. concurrency CI hủy run cùng ref cũ khi có run mới, còn release cancel-in-progress:false để tránh bỏ dở publication. Token không được đưa vào tài liệu hoặc log; chỉ mô tả tên biến và vai trò.
Nguồn: .github/workflows/ci.yml; .github/workflows/release.yml.

## Chương 66 Giải thích ci yml thực tế

CI chạy khi push main/develop, pull request tới main và workflow_dispatch. Job quality-and-tests dùng ubuntu-latest, Python 3.12, requirements-ci.txt, Ruff, compileall src app scripts, pytest xuất JUnit, rồi import app.app và app.api. Upload JUnit dùng if:always để có report cả khi test lỗi.

Job docker-build validate Compose và build Dockerfile.rag với tag food-review-intelligence:ci. CI không download weights, train hoặc rebuild Foody index. Synthetic tests và import không chứng minh model riêng sẵn sàng; demo-preflight thực cần local artifacts. requirements-ci khác runtime dependencies là phân chia mục tiêu môi trường, không phải thiếu bằng chứng build pipeline.
Nguồn: .github/workflows/ci.yml; requirements-ci.txt.

## Chương 67 Giải thích release yml thực tế

Release trigger v* tag hoặc workflow_dispatch với version. Step validate kiểm regex vMAJOR.MINOR.PATCH có thể có prerelease; setup-buildx tạo builder; login-action đăng nhập ghcr.io bằng github.actor/GITHUB_TOKEN; metadata-action sinh tags; build-push-action build Dockerfile.rag và push:true.

Tag push stable tạo ref tag, version không v, major.minor và latest theo cấu hình; prerelease không tạo latest qua điều kiện explicit. Manual dispatch có raw input version và semantics khác tag push; không giả định mọi alias luôn xuất hiện. Git tag v1.0.1 có sẵn nên không tạo lại trong hướng dẫn reproducibility.
Nguồn: .github/workflows/release.yml.

## Chương 68 GHCR và release đã xác minh

GHCR là registry lưu image layers và manifests; URL ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 chỉ một image reference. Tag thuận tiện nhưng có thể thay đổi; digest xác định nội dung manifest. Release hiện xác minh index digest sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a, có linux/amd64 manifest.

CI run 39739640437 và release run 39742439011 đều success tại commit 4229a8b3998392c97f4b7a8c9e3795830285dbce. Đây là cập nhật mới hơn CICD_EVIDENCE.md còn nhắc v1.0.0. Tài liệu lưu kiểm tra read-only ngày 22/10/2026; không sửa workflow hoặc phát hành image mới.
Nguồn: public GitHub Actions run URLs trong Evidence Map; docker buildx imagetools inspect v1.0.1 tại audit.

## Chương 69 Semantic version

Semantic version có ba thành phần MAJOR.MINOR.PATCH. Về nguyên tắc, major báo thay đổi không tương thích, minor thêm chức năng tương thích, patch sửa lỗi tương thích. Trong project, v1.0.1 là tag sau fix runtime Docker; không suy diễn version package pyproject.toml=0.1.0 phải trùng release image tag.

Workflow chỉ kiểm cấu trúc version, không tự chứng minh mức thay đổi đúng quy ước semantic. Khi chuẩn bị release tương lai cần chọn tag chưa tồn tại, chờ CI của đúng commit và xem manifest. Tài liệu mô tả quy trình; không thực hiện commit/push/tag.
Nguồn: .github/workflows/release.yml; pyproject.toml; git tag --list.

## Chương 70 Bản đồ repository

Source map dưới đây nối file với vai trò, input/output và caller. Nhánh src/food, src/baselines, src/proposed_v1/v2 và src/aspect_conditioned là nghiên cứu; src/foody xử lý dữ liệu/inference offline; src/rag và src/rag_v2 có thành phần được V3 tái sử dụng; src/rag_v3 cùng app là đường phục vụ hiện hành.

databricks, crawler, orchestration và một phần src/ml giữ lịch sử hoặc utility còn được tests/audits tham chiếu. Không xóa chúng khi đọc kiến trúc, cũng không đặt chúng vào luồng demo nếu không có caller hiện hành. scripts chứa cả thao tác làm thay đổi artifact và verify; tên script không đủ biết read-only, phải đọc function body.
Nguồn: inventory AST toàn src/app/scripts/tests; README.md; src/cli.py.

```text
.github/workflows/  CI và GHCR release
app/                Streamlit và API
config/             Demo selection
docs/experiments/   Historical research notes
prompts/            Frozen sentiment và RAG prompts
reports/task2/      Review 2 evidence
reports/final/      Accepted demo summaries
scripts/            Research, verification, launcher
src/                Research và runtime modules
tests/              Unit/synthetic/acceptance checks
data/ models/ state/  Local artifacts ngoài Git
```

Bảng 27. Main file map

| File / main symbol | Input → output | Caller / phase |
| --- | --- | --- |
| src/cli.py::main | argv → exit code/command result | python -m src.cli; entry point |
| src/food/adapters.py::adapt_vn_msasar | raw DataFrame + provenance → canonical rows, rejects, counts | src.food.data.prepare; research preparation |
| src/food/split.py::leakage_groups | canonical frame → component ID mỗi dòng | assign_splits/load_splits; research |
| src/food/split.py::assign_splits | frame + FoodConfig → frame có split + metadata | split_dataset; research |
| src/baselines/tfidf_logreg.py::build_pipeline | trial, weight, seed → sklearn Pipeline | baseline runner; research model |
| src/baselines/rule_based.py::VietnameseRuleBased | text list → sentiment labels | baseline runner; research baseline |
| src/baselines/metrics.py::scores | truth + predictions → accuracy và averaged metrics | baseline runner; research evaluation |
| src/proposed_v1/runner.py::freeze_prompts | train/val/test frame + paths → prompt hashes và examples | V1 runner; historical experiment |

Nguồn: source code + AST inventory. Loại: SOURCE AUDIT.

Bảng 28. Main file map

| File / main symbol | Input → output | Caller / phase |
| --- | --- | --- |
| src/proposed_v1/runtime.py::LocalQwen | config + provenance → managed llama-server/session | LLMGateway hoặc experiment runner; shared runtime |
| src/foody/cleaning.py::clean | Foody raw frame + time → processed frame giữ rows | prepare; offline demo preparation |
| src/foody/aspect.py::grouped_targets | frozen row frame → text-group multi-label targets | train; research aspect |
| src/foody/aspect.py::train | frozen split và saved guards → model bundle + test metrics | explicit CLI train-aspect-baseline; research training only |
| src/foody/enrichment.py::predict_observations | processed + 2 saved models → predictions + timing | enrich; offline inference |
| src/foody/enrichment.py::extract_issues | text, aspects, sentiment → unique issue list | predict_observations; heuristic |
| src/foody/analytics.py::build_mart | enriched artifacts, thresholds → 6 parquet marts và report | foody-build-mart CLI; offline analytics |
| src/foody/pipeline.py::prepare_rag | enriched Parquet → documents.jsonl + hash/count | foody-prepare-rag CLI; offline RAG preparation |

Nguồn: source code + AST inventory. Loại: SOURCE AUDIT.

Bảng 29. Main file map

| File / main symbol | Input → output | Caller / phase |
| --- | --- | --- |
| src/rag/embeddings.py::LocalEmbeddings | EmbeddingSpec + text → normalized float32 vectors | index builder/retriever; shared embedding |
| src/rag/vector_store.py::build_index | embedder, identity, docs → Chroma collection + manifest | RAG build CLI; offline indexing |
| src/rag/cli.py::selected_retriever | saved embedding selection → Retriever | RoutedRetriever; online shared |
| src/rag_v2/lexical.py::BM25Retriever | database/manifest + request → ReviewHits + latency | HybridRetriever; online shared |
| src/rag_v2/hybrid.py::rrf_fuse | rankings + constant → merged ranked hits | HybridRetriever.search_debug; retrieval |
| src/rag_v3/routing.py::route_query | question text → Route | RoutedRetriever/prepare_question; active V3 |
| src/rag_v3/evidence.py::build_packet | request, hits, route → Packet | prepare_question; active V3 |
| src/llm/gateway.py::LLMGateway | config/provenance + request payload → parsed JSON + usage | selected_v3_gateway/service; active shared |

Nguồn: source code + AST inventory. Loại: SOURCE AUDIT.

Bảng 30. Main file map

| File / main symbol | Input → output | Caller / phase |
| --- | --- | --- |
| src/rag_v3/evidence.py::validate_packet_citations | answer, refs, packet, hits, route → cited hits hoặc ValueError | answer_question_v3; active safety |
| src/rag_v3/service.py::answer_question_v3 | retriever, gateway, request → response, hits, telemetry, debug, packet | Streamlit Analyst/CLI; active online |
| src/rag/monitoring.py::record | versions/status/timing/allowed filters → SQLite event | gateway/V3 service; LLMOps |
| src/demo.py::demo_preflight | config path → check results + PASS/FAIL | launcher/CLI; acceptance |
| app/app.py::analyst_page | UI question/filter → answer/evidence/mode UI | Streamlit main; frontend |
| app/api.py::ask | Question HTTP body → legacy grounded response | POST /ask; legacy API service |

Nguồn: source code + AST inventory. Loại: SOURCE AUDIT.

## Chương 71 Walkthrough function và class chính

Đọc chương trình theo dòng dữ liệu hiệu quả hơn đọc tên file tuần tự. Bắt đầu từ app.app.analyst_page hoặc src.cli.main, theo command dispatch tới prepare_question, route_query, search_debug, build_packet, gateway.generate, validation/fallback và record. Với offline research, theo load_splits → build_pipeline → fit train → validation selection → test checkpoint → metrics/artifact.

Walkthrough phía dưới trình bày input, output, logic, caller/callee và failure ở các function thật. Signature và line numbers được lấy bằng AST trong audit; pseudo-code là diễn giải, không phải đoạn source có thể dùng thay production. Các thao tác train/index được mô tả để hiểu và không được chạy lại trong task này.
Nguồn: source hiện tại; scripts/documentation/audit_repository.py.

### main

Nguồn: src/cli.py:10. Vai trò: entry point. Input: argv. Output: exit code/command result. Caller: python -m src.cli.

Pseudo-code và logic: Parse subcommand rồi dispatch sang module tương ứng. Failure cần hiểu: Thiếu artifact hoặc argument không hợp lệ.

Callee được source xác nhận: group.add_argument, sub.add_mutually_exclusive_group, validate_fixture_mode.

### adapt_vn_msasar

Nguồn: src/food/adapters.py:43. Vai trò: research preparation. Input: raw DataFrame + provenance. Output: canonical rows, rejects, counts. Caller: src.food.data.prepare.

Pseudo-code và logic: filter → validate ordinal → normalize → dedup exact tuple. Failure cần hiểu: Schema thiếu hoặc không còn row hợp lệ.

Callee được source xác nhận: normalize_text.

### leakage_groups

Nguồn: src/food/split.py:15. Vai trò: research. Input: canonical frame. Output: component ID mỗi dòng. Caller: assign_splits/load_splits.

Pseudo-code và logic: union các dòng chung review ID hoặc normalized text. Failure cần hiểu: Leakage nếu bỏ grouping trước split.

Callee được source xác nhận: normalize_text.

### assign_splits

Nguồn: src/food/split.py:34. Vai trò: research. Input: frame + FoodConfig. Output: frame có split + metadata. Caller: split_dataset.

Pseudo-code và logic: 64 candidate group splits → score cân đối → chọn cố định. Failure cần hiểu: Không đủ independent groups hoặc thiếu class.

Callee được source xác nhận: (frame.iloc[ids].sentiment.value_counts(normalize=True).reindex(population.index, fill_value=0) - population).abs, (frame.iloc[ids].sentiment.value_counts(normalize=True).reindex(population.index, fill_value=0) - population).abs().sum, (result.loc[result.split == name].sentiment.value_counts(normalize=True) * 100).to_dict, first.split, frame.iloc[ids].sentiment.value_counts(normalize=True).reindex, leakage_groups, result.groupby, result.groupby('review_id').split.nunique.

### build_pipeline

Nguồn: src/baselines/tfidf_logreg.py:19. Vai trò: research model. Input: trial, weight, seed. Output: sklearn Pipeline. Caller: baseline runner.

Pseudo-code và logic: TfidfVectorizer → multinomial LR; fit chỉ khi runner gọi. Failure cần hiểu: Vocabulary rỗng hoặc train thiếu class.

Callee được source xác nhận: LogisticRegression, Pipeline, TfidfVectorizer, tuple.

### VietnameseRuleBased

Nguồn: src/baselines/rule_based.py:104. Vai trò: research baseline. Input: text list. Output: sentiment labels. Caller: baseline runner.

Pseudo-code và logic: longest phrase → local negation/intensifier → sign. Failure cần hiểu: Không hiểu sarcasm/implicit sentiment.

Callee được source xác nhận: normalize_text, normalize_text(text).casefold, self.score, term.split.

### scores

Nguồn: src/baselines/metrics.py:36. Vai trò: research evaluation. Input: truth + predictions. Output: accuracy và averaged metrics. Caller: baseline runner.

Pseudo-code và logic: precision_recall_fscore_support theo LABELS. Failure cần hiểu: Sai label order hoặc khác denominator.

Callee được source xác nhận: accuracy_score, precision_recall_fscore_support.

### freeze_prompts

Nguồn: src/proposed_v1/runner.py:32. Vai trò: historical experiment. Input: train/val/test frame + paths. Output: prompt hashes và examples. Caller: V1 runner.

Pseudo-code và logic: chỉ chọn train examples rồi khóa manifest. Failure cần hiểu: Manifest thay đổi sau selection.

Callee được source xác nhận: json.loads, train.groupby, train.groupby('text').sentiment.nunique, train.groupby('text').sentiment.nunique().eq.

### LocalQwen

Nguồn: src/proposed_v1/runtime.py:38. Vai trò: shared runtime. Input: config + provenance. Output: managed llama-server/session. Caller: LLMGateway hoặc experiment runner.

Pseudo-code và logic: khởi tạo runtime và thu tài nguyên; context manager dọn process sở hữu. Failure cần hiểu: Weights/runtime thiếu hoặc endpoint lỗi.

Callee được source xác nhận: output.splitlines, output.splitlines()[0].split.

### clean

Nguồn: src/foody/cleaning.py:57. Vai trò: offline demo preparation. Input: Foody raw frame + time. Output: processed frame giữ rows. Caller: prepare.

Pseudo-code và logic: normalize → identity → parse date → valid flag → lineage. Failure cần hiểu: Invalid schema; U+FFFD bị đánh dấu không hợp lệ.

Callee được source xác nhận: result.groupby, result.groupby('observation_id').source_row.agg, validate_processed.

### grouped_targets

Nguồn: src/foody/aspect.py:25. Vai trò: research aspect. Input: frozen row frame. Output: text-group multi-label targets. Caller: train.

Pseudo-code và logic: union aspect theo split/text. Failure cần hiểu: Một normalized text đi qua nhiều splits.

Callee được source xác nhận: rows.groupby, rows.groupby('text').split.nunique, rows.groupby('text').split.nunique().gt, rows.groupby('text').split.nunique().gt(1).any, rows.groupby(['split', 'text'], sort=True).agg, rows.groupby(['split', 'text'], sort=True).agg(aspects=('aspect', lambda x: sorted(set(x))), source_review_ids=('review_id', lambda x: sorted(set(x))), source_aspect_rows=('aspect', 'size')).reset_index.

### train

Nguồn: src/foody/aspect.py:54. Vai trò: research training only. Input: frozen split và saved guards. Output: model bundle + test metrics. Caller: explicit CLI train-aspect-baseline.

Pseudo-code và logic: train candidates → validation C/threshold → checkpoint test. Failure cần hiểu: Checksum khác, test marker tồn tại nhưng checkpoint thiếu.

Callee được source xác nhận: MultiLabelBinarizer(classes=classes).fit, bundle['pipeline'].predict_proba, frame.split.value_counts, frame.split.value_counts().to_dict, grouped_targets, groups.loc[groups.split == 'test'].copy, groups.split.value_counts, groups.split.value_counts().to_dict.

### predict_observations

Nguồn: src/foody/enrichment.py:63. Vai trò: offline inference. Input: processed + 2 saved models. Output: predictions + timing. Caller: enrich.

Pseudo-code và logic: valid observation dedup → predict_proba → threshold → issues. Failure cần hiểu: Model classes/threshold không khớp bundle.

Callee được source xác nhận: aspect_bundle['pipeline'].predict_proba, sentiment_model.predict_proba.

### extract_issues

Nguồn: src/foody/enrichment.py:43. Vai trò: heuristic. Input: text, aspects, sentiment. Output: unique issue list. Caller: predict_observations.

Pseudo-code và logic: negative gate → aspect rule → negation filter. Failure cần hiểu: Bỏ sót mixed/implicit complaint.

Callee được source xác nhận: re.search.

### build_mart

Nguồn: src/foody/analytics.py:100. Vai trò: offline analytics. Input: enriched artifacts, thresholds. Output: 6 parquet marts và report. Caller: foody-build-mart CLI.

Pseudo-code và logic: distinct review → aggregates → adjacent-month alerts. Failure cần hiểu: Không có đủ ngày hoặc mẫu số sai nếu bỏ business_rows.

Callee được source xác nhận: frame.groupby, frame.groupby('restaurant_key').restaurant_name.agg, raw.groupby, raw.groupby('restaurant_key').size.

### prepare_rag

Nguồn: src/foody/pipeline.py:16. Vai trò: offline RAG preparation. Input: enriched Parquet. Output: documents.jsonl + hash/count. Caller: foody-prepare-rag CLI.

Pseudo-code và logic: valid predicted reviews → dedup ID → metadata lineage. Failure cần hiểu: ID không nhất quán hoặc file đầu vào thiếu.

Callee được source xác nhận: frame.loc[frame.valid_for_ai & frame.predicted_sentiment.notna()].copy, frame.predicted_sentiment.notna, valid.groupby, valid.groupby('review_id').source_row.agg.

### LocalEmbeddings

Nguồn: src/rag/embeddings.py:27. Vai trò: shared embedding. Input: EmbeddingSpec + text. Output: normalized float32 vectors. Caller: index builder/retriever.

Pseudo-code và logic: FastEmbed ONNX → dimension check → L2 normalize. Failure cần hiểu: Dimension sai hoặc weights không có local.

Callee được source xác nhận: Path, TextEmbedding, ValueError, list, np.asarray.

### build_index

Nguồn: src/rag/vector_store.py:78. Vai trò: offline indexing. Input: embedder, identity, docs. Output: Chroma collection + manifest. Caller: RAG build CLI.

Pseudo-code và logic: validate existing manifest hoặc batch upsert → count check. Failure cần hiểu: Manifest/hash mismatch; không ghi đè index khác.

Callee được source xác nhận: json.loads.

### selected_retriever

Nguồn: src/rag/cli.py:36. Vai trò: online shared. Input: saved embedding selection. Output: Retriever. Caller: RoutedRetriever.

Pseudo-code và logic: normalize saved separators → verify model digest → local embedder. Failure cần hiểu: FileNotFoundError/hash mismatch.

Callee được source xác nhận: json.loads.

### BM25Retriever

Nguồn: src/rag_v2/lexical.py:87. Vai trò: online shared. Input: database/manifest + request. Output: ReviewHits + latency. Caller: HybridRetriever.

Pseudo-code và logic: FTS expression + metadata SQL filters → rank limit. Failure cần hiểu: Source hash mismatch hoặc SQLite thiếu.

Callee được source xác nhận: RetrievalRequest.model_validate, json.loads.

### rrf_fuse

Nguồn: src/rag_v2/hybrid.py:74. Vai trò: retrieval. Input: rankings + constant. Output: merged ranked hits. Caller: HybridRetriever.search_debug.

Pseudo-code và logic: cộng reciprocal rank theo ID; tie-break ID. Failure cần hiểu: Không thể suy meaning probability từ fusion score.

Callee được source xác nhận: scores.get, scores.items.

### route_query

Nguồn: src/rag_v3/routing.py:21. Vai trò: active V3. Input: question text. Output: Route. Caller: RoutedRetriever/prepare_question.

Pseudo-code và logic: detect intent/aspect → chọn BM25/RRF/guard. Failure cần hiểu: Lexical intent detection hiểu sai câu.

Callee được source xác nhận: Route, detect, detected.aspect.upper.

### build_packet

Nguồn: src/rag_v3/evidence.py:45. Vai trò: active V3. Input: request, hits, route. Output: Packet. Caller: prepare_question.

Pseudo-code và logic: compatibility → dedup → cap 3 → refs/aggregates. Failure cần hiểu: Evidence rỗng dẫn insufficient, không cố sinh.

Callee được source xác nhận: _packet_text.

### LLMGateway

Nguồn: src/llm/gateway.py:19. Vai trò: active shared. Input: config/provenance + request payload. Output: parsed JSON + usage. Caller: selected_v3_gateway/service.

Pseudo-code và logic: verify local hash → URL override → HTTP strict JSON parse. Failure cần hiểu: Timeout, duplicate JSON key, malformed output.

Callee được source xác nhận: json.loads, record, yaml.safe_load.

### validate_packet_citations

Nguồn: src/rag_v3/evidence.py:96. Vai trò: active safety. Input: answer, refs, packet, hits, route. Output: cited hits hoặc ValueError. Caller: answer_question_v3.

Pseudo-code và logic: refs/topic/polarity/frequency → clause support. Failure cần hiểu: Heuristic false positive/negative.

Callee được source xác nhận: re.search, re.split.

### answer_question_v3

Nguồn: src/rag_v3/service.py:89. Vai trò: active online. Input: retriever, gateway, request. Output: response, hits, telemetry, debug, packet. Caller: Streamlit Analyst/CLI.

Pseudo-code và logic: prepare → 2 attempts → validate/fallback → record. Failure cần hiểu: Runtime lỗi; vẫn chỉ fallback nếu có evidence.

Callee được source xác nhận: RetrievalRequest.model_validate, V3Draft.model_validate, gateway.generate, packet.generation_payload, record, validate_packet_citations.

### record

Nguồn: src/rag/monitoring.py:11. Vai trò: LLMOps. Input: versions/status/timing/allowed filters. Output: SQLite event. Caller: gateway/V3 service.

Pseudo-code và logic: allowlist filters → ensure columns → insert event. Failure cần hiểu: SQLite contention hoặc state permission.

Callee được source xác nhận: (filters or {}).items, Path, connection.execute, datetime.now, datetime.now(UTC).isoformat.

### demo_preflight

Nguồn: src/demo.py:28. Vai trò: acceptance. Input: config path. Output: check results + PASS/FAIL. Caller: launcher/CLI.

Pseudo-code và logic: read artifacts/counts/hashes/runtime; không train/index. Failure cần hiểu: Thiếu file hoặc frozen hash/count khác.

Callee được source xác nhận: Path, ValueError, _json, _json_from_yaml, _missing_streamlit.

### analyst_page

Nguồn: app/app.py:140. Vai trò: frontend. Input: UI question/filter. Output: answer/evidence/mode UI. Caller: Streamlit main.

Pseudo-code và logic: construct request → direct V3 call → render tables. Failure cần hiểu: Exception được hiển thị RAG unavailable.

Callee được source xác nhận: RetrievalRequest, RoutedRetriever, answer_question_v3, choose_restaurant, hit.metadata.get.

### ask

Nguồn: app/api.py:25. Vai trò: legacy API service. Input: Question HTTP body. Output: legacy grounded response. Caller: POST /ask.

Pseudo-code và logic: resolve restaurant → default gateway → V1 service. Failure cần hiểu: 503 nếu artifact/runtime chưa sẵn sàng.

Callee được source xác nhận: HTTPException, LLMGateway, RetrievalRequest, answer.model_dump, answer_question.

## Chương 72 Model được build ra sao

Sentiment: import source pinned → filter vi/restaurant → NFC/whitespace → sign labels → connected-component split → fit TF-IDF và LR trên train → chọn n-gram/C bằng validation → freeze → test một lần trong protocol baseline → lưu models/tfidf_logreg.joblib → Foody predict_proba. Rating/aspect không đi vào text-only sentiment features.

Aspect: dùng frozen split → group normalized text trong split → union aspect targets → MultiLabelBinarizer theo train classes → TF-IDF + OVR LR → validation C/threshold → checkpoint test → lưu models/aspect_tfidf.joblib. Enrichment chỉ load artifacts, không gọi train.

LLM: lấy weights pretrained đã pin revision/hash → load bằng llama.cpp → prompt inference/evaluation. Không có pipeline pretrain Qwen/Llama/DeepSeek từ raw Foody. Các experiment prompt không cập nhật weights.
Nguồn: src/baselines/runner.py; src/foody/aspect.py; src/foody/enrichment.py; reports/task2/TRAINING_SCOPE.md.

## Chương 73 Fit và transform

fit học vocabulary và IDF từ train; transform dùng đúng vocabulary/IDF đó để mã hóa dữ liệu mới. Trong sklearn Pipeline, fit(train_texts, labels) fit transformer rồi classifier; predict/transform validation/test chỉ áp dụng thành phần đã học. Token chưa có vocabulary không tự tạo chiều mới lúc predict.

Nếu fit TF-IDF trên toàn dataset trước khi split, IDF và vocabulary đã dùng thông tin test dù chưa dùng label. Đó là leakage preprocessing. Code hiện tại đóng gói transformer vào pipeline được fit train-only; đọc source và frozen protocol quan trọng hơn chỉ thấy câu “we split data” trong report.
Nguồn: src/baselines/tfidf_logreg.py; src/baselines/runner.py; tests/test_food_baselines.py.

## Chương 74 Offline research flow

Dataset revision và raw hashes xác định nguồn; preparation hash xác định dữ liệu chuẩn hóa; split hash xác định membership. Runner chọn cấu hình từ validation, lưu model/prompt/protocol hashes, predictions và metrics. MLflow run_id cho phép nối candidate với evidence. DVC khai báo quan hệ dependencies và outputs, không đảm bảo một lệnh reproduce sẽ nhẹ.

Historical experiments đã hoàn tất nên không chạy dvc repro toàn bộ chỉ để xem demo. Có checkpoint/guard tránh vô tình đánh giá test lần hai, nhưng nghiên cứu V2 vẫn công khai test đã được nhìn. Reproducibility nghĩa có thể truy vết và thiết lập lại điều kiện, không có nghĩa mọi hệ điều hành sẽ tạo timing hoặc bit-identical floating point giống nhau.
Nguồn: dvc.yaml; dvc.lock; params.yaml; src/baselines/runner.py; src/proposed_v1/runner.py.

## Chương 75 Offline Foody flow

foody_reviews.csv → immutable snapshot → processed giữ source_row/original text → grouped observations → sentiment/aspect inference → issue rules → enriched join lại mọi dòng → distinct-review marts → documents.jsonl → embedding/Chroma và FTS5/BM25. Mỗi chuyển đổi có hash/manifest hoặc report để theo lineage.

Không xem dedup observation là xóa dữ liệu: original records vẫn ở processed/enriched, predictions được join many-to-one. Không suy ra predicted_negative_rate là tỷ lệ khách thực sự không hài lòng trong dân số, do sample crawl, classifier error và domain shift. RAG lấy những review đã có evidence, không tạo gold labels mới.
Nguồn: src/foody/cleaning.py; src/foody/enrichment.py; src/foody/analytics.py; src/foody/pipeline.py.

## Chương 76 Online query flow

Browser gửi tương tác tới Streamlit. analyst_page tạo RetrievalRequest từ text/filter và chọn gateway 3B. RoutedRetriever kiểm manifest rồi chọn policy; packet gate lọc evidence; gateway gửi chat JSON qua HTTP llama.cpp; validator kiểm từng clause; response cuối mang mode/citations; record ghi telemetry.

Nghiệm thu Hanuri với câu “Nhân viên phục vụ có vấn đề gì không?” trả extractive_fallback có citation thật và event LLMOps. Log đã lưu event 403 với retrieval khoảng 5.027 ms, LLM khoảng 41.969 ms, end-to-end khoảng 47.415 ms trên container CPU. Đây là một request runtime khác accepted GPU/local replay, không dùng để thay các metric benchmark đã đóng băng.
Nguồn: app/app.py::analyst_page; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 77 Testing và acceptance

Unit tests kiểm hàm nhỏ như normalization, label mapping, JSON/citation validation. Synthetic integration nối vài thành phần bằng fixture/fake runtime. Smoke kiểm import hoặc endpoint cơ bản. Acceptance dùng artifact thật để xác nhận đường demo và một câu hỏi thực; không đồng nghĩa đánh giá tổng quát chất lượng.

Kết quả gần nhất được ghi trong bằng chứng và phiên nghiệm thu là 288 passed, 1 warning, Ruff PASS, compileall PASS. Đây là kết quả kiểm tra trước task tài liệu, không phải suite chạy mới lúc viết Word. Test count 287 trong KEY_NUMBERS.json là snapshot cũ. Các test_rag_v3, test_demo_preflight, test_food_baselines, test_foody_intelligence giúp truy vết những hợp đồng chính.
Nguồn: tests/; reports/task2/REVIEW2_STATUS_SUMMARY_VI.md; reports/final/KEY_NUMBERS.json.

## Chương 78 Bảo mật và an toàn câu trả lời

Grounding và fallback giảm việc đưa claim không có evidence; filter ngăn lấy nhầm nhà hàng/ngày; schema cấm field lạ; citations map về review IDs thực. Những guard này là kiểm soát chất lượng trong demo, không phải chứng nhận chống mọi prompt injection hoặc mọi hallucination.

Weights, Foody data, vector stores, .env và SQLite runtime được ignore; CI sử dụng fixtures; model/report mounts RO. Operational logs không lưu raw content. Tuy nhiên data/state mounts RW, input review vẫn là dữ liệu không tin cậy, và evaluation files riêng có thể chứa text. Phải phân biệt kiểm soát đã thực hiện với kiểm toán security chưa có.
Nguồn: .gitignore; .dockerignore; src/rag/monitoring.py; src/rag_v3/evidence.py; docker-compose.yml.

## Chương 79 Kiến trúc cuối cùng

Hình tổng thể tách research offline khỏi demo. Classifier cổ điển tạo nhãn dự đoán; retrieval tìm bằng chứng; LLM diễn đạt; validator/fallback quyết định đầu ra được chấp nhận. Vì thế “LLM everything” không phù hợp evidence hiện tại: TF-IDF phân loại tốt hơn V1 và nhỏ/nhanh hơn trong các đo đã có, còn LLM có khả năng viết câu.

Hình kiến trúc logic không mô tả mọi network hop. Deployment thực có Streamlit gọi modules trực tiếp và kết nối Qwen; backend là service phụ legacy. Các khối MLflow/SQLite/Chroma là storage hoặc thư viện, không phải tất cả đều là container độc lập. Không đưa Databricks vào kiến trúc phục vụ cuối chỉ vì source lịch sử còn trong repository.
Nguồn: reports/task2/figures/final_architecture.png; app/app.py; docker-compose.yml.

![Kiến trúc logic research và demo](../reports/task2/figures/final_architecture.png)

Hình 11. Kiến trúc logic research và demo. Nguồn: reports/task2/figures/final_architecture.png. Deployment hops cần đọc chương Docker; UI không gọi V3 qua FastAPI.

## Chương 80 Điều thành công thất bại và bài học

Rule thành công như baseline dễ giải thích nhưng nhiều neutral false positives. TF-IDF nâng macro-F1 và trở thành classifier demo; neutral vẫn yếu. Qwen V1 vượt rule nhưng thua TF-IDF. V2-A calibration và V2-B aspect input chưa mang cải thiện xác nhận; bài học là chọn theo evidence thay vì độ phức tạp.

RAG V1 chưa tìm tốt known positives; V2 hybrid cải thiện một số truy xuất nhưng sinh câu còn lỗi; V3 giữ useful evidence bằng fallback và guard. Docker từng gặp serialized path Windows/Linux và dependency psutil; sửa đúng nguồn dependency/path giúp nghiệm thu mà không retrain. CI/CD đã build/test/publish image, còn remote deployment không nằm trong phạm vi.
Nguồn: reports/task2/GAP_ANALYSIS.md; reports/task2/RAG_ABLATION_FINAL.md; reports/task2/DOCKER_ACCEPTANCE.md.

## Chương 81 Giới hạn và bước nghiên cứu tiếp theo

Giới hạn dữ liệu: label aspect-level có xung đột text-only; neutral ít; Foody không có gold labels; tên nhà hàng chưa là ID chính thức; sampling review có thiên lệch. Giới hạn model: probability chưa calibrated Foody, issue heuristic, zero-support aspects và một số lựa chọn parameter chưa có controlled search.

Giới hạn RAG: sáu query với relevance chưa đầy đủ, truncation embedding dài, rule support không phải human entailment, latency khác run/hardware và generator fallback nhiều. Ablation là observed progression, không có packet-off/validator-off/fallback-off controls. GPU Docker chưa được xác minh; không train LLM from scratch; CD không phải remote production deployment.

Ưu tiên nghiên cứu tiếp theo là thêm relevance/human support labels độc lập, đánh giá chunked index riêng cho review dài và đo robustness trên domain mới. Đây là khuyến nghị dựa trên failure evidence, không triển khai feature mới hoặc tự nhận V4 đã tồn tại.
Nguồn: reports/task2/TRAINING_SCOPE.md; reports/task2/LLM_BENCHMARK.md; reports/task2/CHUNKING_DECISION.md.

## Chương 82 Bảng lựa chọn tham số

Bảng và các thẻ phía dưới phân biệt hai loại bằng chứng. Validation-selected nghĩa có các ứng viên và điểm validation được lưu; engineering choice nghĩa giá trị đang dùng nhưng chưa có controlled experiment độc lập để chứng minh tối ưu. Một parameter có thể là architecture-fixed, như embedding dimension, thay vì knob tự do.

Hãy bảo vệ quyết định bằng thứ tự: định nghĩa → ảnh hưởng → ứng viên thật → metric chọn → kết quả → giới hạn → điều dự kiến khi tăng/giảm. Các dự kiến tăng/giảm là lý thuyết có điều kiện, không phải số đo đã chạy. Không dùng từ optimal cho grid ba trial hoặc smoke sáu ca.
Nguồn: src/baselines/tfidf_logreg.py; src/foody/aspect.py; src/rag_v2/hybrid.py; configs và CSV candidate.

Bảng 31. Parameter selection summary

| Parameter | Selected | Selection type | Evidence |
| --- | --- | --- | --- |
| Sentiment ngram_range | (1,2) | VALIDATION_SELECTED | reports/baselines/tfidf_experiments.csv |
| Sentiment C | 2 | VALIDATION_SELECTED | src/baselines/tfidf_logreg.py |
| max_features | 20000 | ENGINEERING | src/baselines/tfidf_logreg.py |
| min_df | 2 | ENGINEERING | src/baselines/tfidf_logreg.py |
| sublinear_tf | True | ENGINEERING | src/baselines/tfidf_logreg.py |
| class_weight sentiment | balanced | MEASURED_COMPARISON | reports/task2/imbalance_comparison.csv |
| max_iter | 1500 | ENGINEERING | src/baselines/tfidf_logreg.py |
| Sentiment solver | lbfgs | ENGINEERING | src/baselines/tfidf_logreg.py |

Nguồn: registry đối chiếu code/config/candidate CSV. Loại: CONFIGURED + MEASURED.

Bảng 32. Parameter selection summary

| Parameter | Selected | Selection type | Evidence |
| --- | --- | --- | --- |
| Seed | 42 | CONFIGURED_AND_MEASURED | reports/task2/baseline_three_seed.csv |
| Aspect C | 2 | VALIDATION_SELECTED | reports/aspect_classifier/validation_comparison.csv |
| Aspect threshold | 0.5 | VALIDATION_SELECTED | reports/aspect_classifier/validation_comparison.csv |
| Chunk policy | one review one document | ENGINEERING_WITH_SIMULATION | reports/task2/chunking_comparison.csv |
| Embedding model | multilingual MiniLM L12 v2 | DEVELOPMENT_SELECTED | reports/rag/embedding_comparison.csv |
| Embedding dimensions | 384 | ARCHITECTURE_FIXED | src/rag/embeddings.py |
| top_k | 5 demo; 10 retrieval evaluation | ENGINEERING | config/demo.yaml; src/rag_v3/cli.py |
| Dense và lexical top_n | 20 mỗi nhánh | ENGINEERING | src/rag_v2/hybrid.py |

Nguồn: registry đối chiếu code/config/candidate CSV. Loại: CONFIGURED + MEASURED.

Bảng 33. Parameter selection summary

| Parameter | Selected | Selection type | Evidence |
| --- | --- | --- | --- |
| RRF constant | 60 | ENGINEERING | src/rag_v2/hybrid.py::rrf_fuse |
| BM25 k1 và b | SQLite FTS5: 1.2 và 0.75 | LIBRARY_DEFAULT | src/rag_v2/lexical.py; https://www.sqlite.org/fts5.html |
| Evidence reranking | +0.004 aspect; +0.006/-0.012 polarity; ±0.006 issue | ENGINEERING | src/rag_v2/hybrid.py::search_debug |
| Evidence packet cap | 3 review | ENGINEERING | src/rag_v3/evidence.py::build_packet |
| Packet text cap | 350 ký tự | ENGINEERING | src/rag_v3/evidence.py::_packet_text |
| LLM demo | Qwen2.5 3B Q4_K_M | LOCAL_ACCEPTANCE_SELECTED | reports/rag_v3/generation_metrics.json |
| Quantization | Q4_K_M | ENGINEERING | qwen_v1.yaml; qwen_v3_3b.yaml |
| Temperature | 0 | ENGINEERING | src/llm/gateway.py::generate |

Nguồn: registry đối chiếu code/config/candidate CSV. Loại: CONFIGURED + MEASURED.

Bảng 34. Parameter selection summary

| Parameter | Selected | Selection type | Evidence |
| --- | --- | --- | --- |
| Context length | 2048 | ENGINEERING | qwen_v3_3b.yaml; docker-compose.yml |
| Output token cap | 32 sentiment; 128 V3 | ENGINEERING | qwen_v1.yaml; src/rag_v3/service.py |
| Attempts | 2 | ENGINEERING | src/rag_v3/service.py |
| CPU threads | 8 local config | ENGINEERING | qwen_v1.yaml; qwen_v3_3b.yaml |
| GPU layers | 99 requested; Docker CPU observed | CONFIGURED_WITH_LIMIT | docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md |
| Ports | 8501 UI; 8000 API; 8193 Compose Qwen; 8194 local 3B | ENGINEERING | docker-compose.yml; qwen_v3_3b.yaml |
| Mount permissions | models/reports RO; data/state RW | ENGINEERING | docker-compose.yml |
| Alert thresholds | n≥10; rate delta≥0.2; rating delta≤−1.0 | ENGINEERING | src/foody/analytics.py::alerts |

Nguồn: registry đối chiếu code/config/candidate CSV. Loại: CONFIGURED + MEASURED.

## Chương 83 Phiếu bảo vệ quyết định kỹ thuật

Các thẻ quyết định dưới đây dùng để trả lời “tại sao giá trị này”. Mỗi thẻ chỉ ra lựa chọn đang dùng, alternatives đã có hoặc chưa thử, evidence và uncertainty. Có thể mở thẳng file nguồn ghi ở cuối thẻ khi giảng viên hỏi. Cụm “chưa có controlled experiment” là giới hạn khoa học, không phải bỏ qua giải thích kỹ thuật.
Nguồn: parameter registry và Evidence Map trong tài liệu này.

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

## Chương 84 Câu hỏi bảo vệ và trả lời

Phần Q&A dùng hai tầng: câu ngắn để trả lời trực tiếp và giải thích sâu để nối về code, công thức, evidence. Không học thuộc số lẻ mà quên đơn vị đếm hoặc phạm vi. Với metric chưa đo, câu trả lời đúng là nêu thiếu evidence và cách kiểm chứng cần làm, không điền một giá trị ước đoán.
Nguồn: source audit; reports/task2/; các bảng kiểm chứng trong tài liệu này.

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

### Câu hỏi 13 Complaint rate có phải aspect sentiment không?

Trả lời ngắn: Data mart là bảng đã tổng hợp cho một câu hỏi nghiệp vụ.

Giải thích sâu: business_rows loại trùng review_id trước tổng hợp. Mẫu số của sentiment là review hợp lệ có prediction; mẫu số rating chỉ gồm numeric rating trong [0,10]. Complaint rate kết hợp overall negative và aspect presence, không phải xác suất aspect-level sentiment gold. Một review nhiều aspect có thể đóng góp vào nhiều tỷ lệ, nên không buộc tổng tỷ lệ aspect bằng 100%.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Overall-negative + aspect-presence là proxy.

Evidence và file/code để mở: src/foody/analytics.py; reports/foody_intelligence/mart.json.

### Câu hỏi 14 Rule baseline xử lý phủ định ra sao?

Trả lời ngắn: VietnameseRuleBased tách token và dấu câu; khớp cụm lexicon dài nhất không chồng lấp.

Giải thích sâu: EXAMPLE: “không ngon” đảo tín hiệu ngon thành âm. “rất ngon nhưng chậm” có thể cộng 1,5 và −1, ra positive: đó là hành vi của quy tắc, không bảo đảm đúng nhãn aspect. Rule không học trọng số và không đọc gold, rating hoặc aspect. Nó dễ giải thích và nhanh nhưng thiếu từ vựng, thành ngữ và sarcasm.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Cửa sổ 3 token không phải parser ngữ nghĩa toàn câu.

Evidence và file/code để mở: src/baselines/rule_based.py; reports/baselines/rule_based_test_metrics.json.

### Câu hỏi 15 TF IDF trong code dùng công thức nào?

Trả lời ngắn: TF-IDF chuyển câu thành vector mà mỗi chiều ứng với một token hoặc n-gram trong vocabulary train.

Giải thích sâu: THEORY: cách giới thiệu phổ biến dùng TF=count/độ dài và IDF=ln(N/df). PROJECT CONFIG: TfidfVectorizer dùng sublinear_tf=True nên TF=1+ln(count) khi count>0; smooth_idf mặc định cho IDF=ln((1+N)/(1+df))+1, sau đó chuẩn hóa L2. Không được lấy công thức TF chuẩn hóa độ dài làm mô tả chính xác implementation.

Công thức: F03–F05. Điểm dễ nhầm: Phân biệt công thức nhập môn với sublinear TF/smoothed IDF.

Evidence và file/code để mở: src/baselines/tfidf_logreg.py::build_pipeline; tài liệu TfidfVectorizer scikit-learn 1.7.

### Câu hỏi 16 Vì sao dùng bigram?

Trả lời ngắn: Ba trial thật là unigram C=1, unigram+bigram C=1 và unigram+bigram C=2.

Giải thích sâu: max_features=20.000 giới hạn vocabulary, min_df=2 bỏ token xuất hiện trong ít hơn hai document train, sublinear_tf=True giảm ưu thế từ lặp. max_iter=1.500 là trần solver, lbfgs là solver sentiment, random_state=42 cố định protocol. Các giá trị này không có sweep độc lập trong repo. Tăng vocabulary có thể giữ tín hiệu hiếm nhưng tăng kích thước và overfit; tăng min_df giảm nhiễu nhưng có thể mất slang hiếm.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Chỉ chọn tốt nhất trong ba trial đã đo.

Evidence và file/code để mở: reports/baselines/tfidf_experiments.csv; src/baselines/tfidf_logreg.py.

### Câu hỏi 17 C lớn có nghĩa regularization mạnh hơn không?

Trả lời ngắn: Regularization hạn chế nghiệm quá phụ thuộc các mẫu train.

Giải thích sâu: PROJECT RESULT: trong cặp cùng bigram, đổi C=1 sang 2 tăng validation macro-F1 từ 0,700294 lên 0,709242. Chỉ có bằng chứng cho hai điểm đó; không suy ra C=10 sẽ tốt hơn. Mô hình được fit train rồi chọn bằng validation, không refit train+validation trước test trong protocol đã lưu.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: C là nghịch đảo mức regularization.

Evidence và file/code để mở: src/baselines/runner.py; reports/baselines/tfidf_experiments.csv; reports/baselines/tfidf_selection.json.

### Câu hỏi 18 LR ba lớp dùng sigmoid hay softmax?

Trả lời ngắn: Một classifier tuyến tính tính score z=wᵀx+b.

Giải thích sâu: Training tối ưu hàm mất mát có regularization và class weights. predict chọn lớp có xác suất lớn nhất, predict_proba cung cấp vector xác suất. Decision boundary là nơi score của hai lớp bằng nhau. Các xác suất này chưa được calibration trên Foody; giá trị 0,9 không tự chứng minh 90% đúng trong miền dữ liệu mới.

Công thức: F06–F07. Điểm dễ nhầm: Sentiment multinomial khác OVR aspect.

Evidence và file/code để mở: src/baselines/tfidf_logreg.py; src/foody/aspect.py; tài liệu LogisticRegression scikit-learn 1.7.

### Câu hỏi 19 Macro F1 có bằng F1 từ macro P và R không?

Trả lời ngắn: Confusion matrix có hàng là gold và cột là predicted.

Giải thích sâu: Macro-F1 lấy trung bình F1 từng lớp, không phải F1 tính từ macro-precision và macro-recall. Weighted-F1 dùng support làm trọng số nên lớp positive đông có ảnh hưởng lớn. Micro-F1 gom TP/FP/FN trước khi tính; trong single-label đủ nhãn nó bằng accuracy, nhưng trong multi-label không còn như vậy. zero_division=0 xử lý mẫu số bằng 0 trong code.

Công thức: F11–F12. Điểm dễ nhầm: Trung bình F1 từng lớp trước.

Evidence và file/code để mở: src/baselines/metrics.py::scores, class_report; reports/baselines/tfidf_test_metrics.json.

### Câu hỏi 20 Tại sao vẫn dùng TF IDF khi đã có Qwen?

Trả lời ngắn: Rule-Based đạt test accuracy 0,505073, macro-F1 0,431279.

Giải thích sâu: Classifier TF-IDF được dùng trong Foody inference vì kết quả đã đo tốt hơn Qwen V1 cho phân loại text-only, latency trung bình single-sample 0,365186 ms và artifact 0,342442 MB. Các timing này là run local riêng, không phải SLA production hoặc speedup đối chứng trên mọi thiết bị. Qwen đảm nhiệm sinh câu từ bằng chứng, một năng lực khác với gán nhãn.

Công thức: F22. Điểm dễ nhầm: So sánh task classification và generation riêng.

Evidence và file/code để mở: reports/baselines/baseline_comparison.csv; reports/task2/FEASIBILITY.csv; src/foody/enrichment.py.

### Câu hỏi 21 Ba seed cùng điểm có nghĩa model tuyệt đối ổn định?

Trả lời ngắn: Seed điều khiển các bước ngẫu nhiên; không phải mọi solver đều nhạy với seed.

Giải thích sâu: PROJECT RESULT: cả ba có test macro-F1 0,682854, accuracy 0,809470, weighted-F1 0,812104 và neutral F1 0,413043; sample SD bằng 0. Điều đó phù hợp lbfgs gần như xác định trong setup này. Không được suy ra độ bất định bằng 0 trên các split hoặc domain khác; chỉ random_state được thay trong phép lặp này.

Công thức: F21. Điểm dễ nhầm: Không đo độ nhạy đối với split/domain mới.

Evidence và file/code để mở: reports/task2/baseline_three_seed.csv; reports/task2/linearsvc_validation_selection.csv; scripts/task2_classical_comparison.py.

### Câu hỏi 22 Qwen V1 có được train bằng Foody không?

Trả lời ngắn: V1 dùng Qwen2.5-1.5B-Instruct-GGUF Q4_K_M, chạy llama.cpp b11429.

Giải thích sâu: Ba prompt đóng băng: v1_a tối giản, v1_b định nghĩa nhãn, v1_c thêm ba ví dụ train-only không xung đột. Chọn bằng validation macro-F1, rồi JSON validity và latency. Qwen chỉ nhận text, phải trả JSON sentiment thuộc ba nhãn. Temperature=0, seed=42, output cap=32, tối đa hai attempts; parser/schema không âm thầm đổi free text thành label.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Pretrained inference khác fine-tuning và pretraining.

Evidence và file/code để mở: qwen_v1.yaml; src/proposed_v1/runner.py; reports/proposed_v1/qwen_prompt_comparison.csv; reports/proposed_v1/qwen_resource_report.json.

### Câu hỏi 23 Vì sao chọn prompt v1_c?

Trả lời ngắn: V1 dùng Qwen2.5-1.5B-Instruct-GGUF Q4_K_M, chạy llama.cpp b11429.

Giải thích sâu: Ba prompt đóng băng: v1_a tối giản, v1_b định nghĩa nhãn, v1_c thêm ba ví dụ train-only không xung đột. Chọn bằng validation macro-F1, rồi JSON validity và latency. Qwen chỉ nhận text, phải trả JSON sentiment thuộc ba nhãn. Temperature=0, seed=42, output cap=32, tối đa hai attempts; parser/schema không âm thầm đổi free text thành label.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Ví dụ few-shot chỉ từ train.

Evidence và file/code để mở: qwen_v1.yaml; src/proposed_v1/runner.py; reports/proposed_v1/qwen_prompt_comparison.csv; reports/proposed_v1/qwen_resource_report.json.

### Câu hỏi 24 V1 có improvement signal không?

Trả lời ngắn: V1 sai 237/887 mẫu; TF-IDF sai 169.

Giải thích sâu: failure_counts cho sarcasm 9 lỗi trên 37 mẫu, mixed-marker 45/121, negation-marker 42/208, short text 33/93 và conflicting text 16/24. Các nhóm chồng lấp; chỉ sarcasm lấy nhãn nguồn, các marker khác là proxy lexical. Không cộng các tử số thành tổng lỗi và không coi proxy là annotation thủ công về hiện tượng ngôn ngữ.

Công thức: F22. Điểm dễ nhầm: Có so với rule, không có so với TF-IDF.

Evidence và file/code để mở: reports/task2/failure_counts.csv; reports/proposed_v1/qwen_test_metrics.json; reports/baselines/tfidf_classification_report.csv.

### Câu hỏi 25 Neutral recall tăng tại sao F1 vẫn kém?

Trả lời ngắn: V1 sai 237/887 mẫu; TF-IDF sai 169.

Giải thích sâu: failure_counts cho sarcasm 9 lỗi trên 37 mẫu, mixed-marker 45/121, negation-marker 42/208, short text 33/93 và conflicting text 16/24. Các nhóm chồng lấp; chỉ sarcasm lấy nhãn nguồn, các marker khác là proxy lexical. Không cộng các tử số thành tổng lỗi và không coi proxy là annotation thủ công về hiện tượng ngôn ngữ.

Công thức: F09–F11. Điểm dễ nhầm: Overprediction tạo nhiều false positives.

Evidence và file/code để mở: reports/task2/failure_counts.csv; reports/proposed_v1/qwen_test_metrics.json; reports/baselines/tfidf_classification_report.csv.

### Câu hỏi 26 V2 A có nhận aspect không?

Trả lời ngắn: V2-A vẫn text-only.

Giải thích sâu: V2-B ở src/aspect_conditioned là protocol khác: text+aspect. Qwen text+aspect test macro-F1 0,602203; TF-IDF text+aspect 0,665514. Không được gọi V2-A là aspect-conditioned như một câu trong GAP_ANALYSIS/Q&A cũ. Hai protocol cần cột input riêng và không được dùng kết quả này làm benchmark text-only công bằng tuyệt đối.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: V2-A text-only; V2-B text+aspect riêng.

Evidence và file/code để mở: qwen_v2.yaml; qwen_aspect.yaml; reports/proposed_v2/prompt_comparison.csv; reports/aspect_conditioned/comparison.csv.

### Câu hỏi 27 Aspect multi label khác sentiment multi class ra sao?

Trả lời ngắn: Sentiment là multi-class: mỗi dòng một nhãn.

Giải thích sâu: Pipeline gồm TF-IDF unigram+bigram và OneVsRest Logistic Regression. Mỗi aspect có classifier nhị phân độc lập. Giá trị predict_proba ≥ threshold được chọn, cho phép không nhãn hoặc nhiều nhãn. C∈{0,5;2}, threshold∈{0,3;0,5;0,7}; chọn C=2, threshold=0,5 theo validation micro-F1, sau đó macro-F1 và C nhỏ hơn.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Một text có thể có nhiều aspect.

Evidence và file/code để mở: src/foody/aspect.py; reports/aspect_classifier/selection.json; reports/aspect_classifier/validation_comparison.csv.

### Câu hỏi 28 Exact match và micro F1 đo gì?

Trả lời ngắn: Micro precision/recall cộng TP, FP, FN trên mọi cặp mẫu–aspect.

Giải thích sâu: EXAMPLE: gold={food,service}, predicted={food}; food đóng góp TP, service đóng góp FN, exact match của mẫu bằng 0. PROJECT RESULT: test micro-F1=0,832277; macro-F1=0,633628; exact match=0,726474; trung bình 1,063990 nhãn dự đoán/mẫu. Ba chỉ số đo những điều khác nhau nên không chọn một số rồi gọi chung là accuracy aspect.

Công thức: F14. Điểm dễ nhầm: Thiếu một nhãn làm exact-match=0 nhưng vẫn có TP.

Evidence và file/code để mở: src/foody/aspect.py::scores; reports/aspect_classifier/test_metrics.json.

### Câu hỏi 29 Room và amenities F1 bằng 0 nói gì?

Trả lời ngắn: Bảng per-aspect bên dưới cho thấy food, service, price có support lớn hơn các aspect hiếm.

Giải thích sâu: amenities và room có test support=0, F1=0 do zero_division=0 và vẫn nằm trong macro tất cả chín nhãn. Không có evidence về năng lực phát hiện hai lớp này trên test; cũng không được tự bỏ chúng để cải thiện macro-F1 công bố. Chỉ có thể thêm một phép phân tích hỗ trợ với mẫu số nói rõ, giữ metric gốc.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Support=0 không đo năng lực lớp.

Evidence và file/code để mở: reports/aspect_classifier/test_per_aspect.csv; src/foody/aspect.py.

### Câu hỏi 30 Issue extraction có accuracy bao nhiêu?

Trả lời ngắn: extract_issues chỉ xét text khi overall predicted sentiment là negative và aspect tương ứng được dự đoán.

Giải thích sâu: Code kiểm tra phủ định ngay trước cụm để tránh “không đắt” thành expensive. Nó không hiểu mọi sarcasm hoặc mixed sentiment; negative tổng thể có thể bỏ sót phàn nàn cục bộ trong review nhìn chung positive. Method được gắn heuristic_v1, không có supervised issue accuracy. Người bảo vệ nên gọi đây là tín hiệu hỗ trợ đọc review, không phải ground-truth complaint mining.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Không có gold issue benchmark; N/A.

Evidence và file/code để mở: src/foody/enrichment.py::ISSUE_RULES, extract_issues; reports/foody_intelligence/issue_rules.json.

### Câu hỏi 31 RAG có loại bỏ hallucination hoàn toàn không?

Trả lời ngắn: LLM có thể sinh câu nghe hợp lý nhưng không có căn cứ trong dữ liệu nhà hàng.

Giải thích sâu: EXAMPLE: hỏi “Nhân viên phục vụ có vấn đề gì không?” tại Hanuri. Hệ thống cần review về service và đúng chiều phàn nàn; review chỉ khen giá rẻ không đủ trả lời. Không thấy bằng chứng phù hợp thì trả insufficient evidence. Có bằng chứng nhưng Qwen viết sai thì dùng extractive fallback. RAG không biến một vài review thành thống kê đại diện về toàn bộ khách hàng.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Validator heuristic không phải oracle.

Evidence và file/code để mở: src/rag_v3/service.py; src/rag_v3/evidence.py; reports/task2/DOCKER_ACCEPTANCE.md.

### Câu hỏi 32 Token có phải từ tiếng Việt không?

Trả lời ngắn: Document là đơn vị nội dung có định danh và metadata; chunk là phần được cắt từ một document; token là đơn vị tokenizer mã hóa, có thể nhỏ hơn một từ tiếng Việt.

Giải thích sâu: Chunk size C giới hạn số token; overlap O lặp phần giáp ranh để giữ liên tục; stride S=C−O là bước dịch. Chunk nhỏ giảm nội dung thừa nhưng có thể cắt mất quan hệ phủ định hoặc ngữ cảnh. Chunk lớn giữ nhiều nghĩa hơn nhưng tăng chi phí và có nguy cơ bị truncation. Overlap tăng số token lưu/nhúng và đòi hỏi dedup khi tổng hợp evidence.

Công thức: F17. Điểm dễ nhầm: Hai tokenizer không được cộng tổng token với nhau.

Evidence và file/code để mở: scripts/task2_rag_accounting.py; reports/task2/CHUNKING_DECISION.md.

### Câu hỏi 33 T=900 C=256 O=32 có mấy chunk?

Trả lời ngắn: THEORY: với T>0, 0≤O<C, N=max(1, ceil((T−C)/(C−O))+1).

Giải thích sâu: EXAMPLE — không phải số liệu project: T=900, C=256, O=32. S=224; (900−256)/224=2,875; ceil=3; N=4. Tổng vị trí token qua các chunk là T+(N−1)×O=996 nếu cửa sổ cuối được cắt đúng tại cuối text. Phải tính trên từng review rồi cộng, không nối 32.457 review thành một chuỗi lớn.

Công thức: F15–F16. Điểm dễ nhầm: Ví dụ minh họa, không phải index thật.

Evidence và file/code để mở: scripts/task2_rag_accounting.py; phụ lục công thức của tài liệu này.

### Câu hỏi 34 Tại sao giữ one review one document?

Trả lời ngắn: prepare_rag lọc valid_for_ai có prediction và drop_duplicates(review_id), tạo JSONL với id, text, metadata.

Giải thích sâu: Giới hạn quan trọng: MiniLM runtime được ghi nhận truncation 128 token. Có 11.235 review, tức 34,615029%, dài hơn 128 content tokens; phần đuôi có thể không ảnh hưởng embedding dù BM25 và evidence còn full text. Mean=115,550297, median=92, p95=288, max=2.124 token. 2.239 review vượt 256 và 222 vượt 512.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Có truncation limitation; chưa chứng minh optimal.

Evidence và file/code để mở: src/foody/pipeline.py::prepare_rag; reports/task2/rag_token_statistics.json; reports/task2/chunking_comparison.csv.

### Câu hỏi 35 Chunk comparison có rebuild index không?

Trả lời ngắn: Bảy policy được mô phỏng trên độ dài token thực, giữ ranh giới review và metadata.

Giải thích sâu: Thời gian thay thế được ước lượng bằng chunk_count / throughput đã đo. Không có embedding hoặc retrieval chạy lại trong các dòng simulation. Bảng dùng chữ DERIVED cho số chunk và estimated_seconds; thời gian index gốc là MEASURED. Khi đổi policy thật phải bổ sung chunk_id, aggregation về review_id và bộ relevance để đánh giá.

Công thức: F16,F23. Điểm dễ nhầm: Chỉ simulation/workload estimate.

Evidence và file/code để mở: reports/task2/chunking_comparison.csv; reports/task2/embedding_workload.csv.

### Câu hỏi 36 384 dimensions do nhóm tune ra phải không?

Trả lời ngắn: Embedding ánh xạ text sang vector số để so sánh gần nhau theo biểu diễn học được.

Giải thích sâu: Model được chọn là sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, dùng bản ONNX của Qdrant qua FastEmbed trên CPU. LocalEmbeddings chuẩn hóa vector L2 và kiểm tra dimension=384. 384 là kích thước kiến trúc model, không phải hyperparameter nhóm tune từ 128 lên 384. Repository không dùng SentenceTransformer trực tiếp cho runtime hiện hành dù tên model thuộc họ Sentence Transformers.

Công thức: F18. Điểm dễ nhầm: Đó là architecture output của selected model.

Evidence và file/code để mở: src/rag/embeddings.py; reports/rag/embedding_selection.json; model card Sentence Transformers.

### Câu hỏi 37 Có so sánh embedding model không?

Trả lời ngắn: Có một so sánh nhỏ thật, không phải không có benchmark.

Giải thích sâu: Potion nhanh hơn nhiều trong đo pool nhưng chất lượng theo nhãn dương đã biết thấp hơn. Pool nhỏ và labels chưa đầy đủ; không có exhaustive embedding model benchmark. Chọn MiniLM trong hai ứng viên không chứng minh thắng mọi encoder hoặc tối ưu với full index. Full-index metric giảm so với pool là điều cần giải thích vì không gian cạnh tranh tăng.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Có hai model/pool 612; không exhaustive.

Evidence và file/code để mở: src/rag/evaluation.py::compare_candidates; reports/rag/embedding_comparison.csv.

### Câu hỏi 38 Raw vector memory có bằng Chroma disk không?

Trả lời ngắn: DERIVED: 32.457 × 384 × 4 = 49.853.952 bytes = 49,853952 MB = 47,544434 MiB cho payload float32.

Giải thích sâu: Chroma còn metadata, text, HNSW, SQLite và overhead; model ONNX và runtime cũng chiếm RAM riêng. Không cộng model disk size với raw vector estimate rồi gọi đó là VRAM. Appendix cung cấp phép tính chính xác bằng Python và nguồn N,d,dtype.

Công thức: F18. Điểm dễ nhầm: Chưa gồm metadata, text, HNSW/SQLite overhead.

Evidence và file/code để mở: data/foody/vector_store/index_manifest.json; src/rag/embeddings.py::_embed.

### Câu hỏi 39 BM25 k1 và b lấy ở đâu?

Trả lời ngắn: BM25 đánh giá mức phù hợp từ khóa bằng tần suất, độ hiếm của term và chuẩn hóa độ dài document.

Giải thích sâu: PROJECT CONFIG: src/rag_v2/lexical.py gọi bm25(reviews_fts) của SQLite FTS5, dùng unicode61 remove_diacritics 2. Code không tune k1/b; tài liệu SQLite ghi cố định k1=1,2 và b=0,75 cho hàm này. SQLite trả số âm để rank nhỏ hơn tốt hơn; code đảo dấu khi tạo ReviewHit.score. FTS query ghép unigram/bigram/trigram bằng OR, quote token và bind SQL parameters.

Công thức: F25. Điểm dễ nhầm: SQLite library constants, không project tuning.

Evidence và file/code để mở: src/rag_v2/lexical.py; SQLite FTS5 bm25 documentation.

### Câu hỏi 40 RRF tại sao không cộng score trực tiếp?

Trả lời ngắn: RRF(d)=Σ_r 1/(k+rank_r(d)); mỗi retriever góp một số theo thứ hạng, không dùng trực tiếp score của nó.

Giải thích sâu: EXAMPLE: document A rank 1 và 4 có score 1/61+1/64≈0,032018; B rank 2 và 2 có 2/62≈0,032258. B nhỉnh hơn vì xuất hiện tốt ở cả hai. Đây là số minh họa, không phải retrieval score lưu của Hanuri.

Công thức: F24. Điểm dễ nhầm: Score BM25 và cosine khác scale.

Evidence và file/code để mở: src/rag_v2/hybrid.py::rrf_fuse, RetrievalConfig.

### Câu hỏi 41 Hit at k trong báo cáo có đúng binary hit không?

Trả lời ngắn: THEORY: Hit@k(q)=1 nếu top-k có ít nhất một relevant document, ngược lại 0; mean Hit@k lấy trung bình trên query.

Giải thích sâu: AUDIT: known_positive_scores trong src/rag/evaluation.py thực sự tính |top-k ∩ known positives|/|known positives|. scripts/evaluate_rag_v3_retrieval.py đổi tên trung bình này thành known_hit_at_5/10. Vì vậy giá trị 0,083333 đã công bố phải được mô tả là macro known-positive recall, không phải binary Hit@k. Tài liệu giữ nguyên số và nêu tên cột lịch sử để truy vết, không sửa experiment.

Công thức: F19,F20. Điểm dễ nhầm: Tên cột cũ chứa known-positive recall; phải chú thích.

Evidence và file/code để mở: src/rag/evaluation.py::known_positive_scores; scripts/evaluate_rag_v3_retrieval.py; reports/rag_v3/retrieval_policy_rows.csv.

### Câu hỏi 42 MRR 0.166667 nghĩa là gì?

Trả lời ngắn: MRR nhìn vị trí relevant đầu tiên: query có rank r góp 1/r, không tìm thấy góp 0.

Giải thích sâu: PROJECT RESULT: V3 routed MRR known-positive=0,166667 trên sáu câu, tức tổng reciprocal ranks bằng 1. Điều này không có nghĩa 16,7% review corpus liên quan. Cần đọc query rows và tập known positives chưa đầy đủ để hiểu rank; reviewer chưa gán nhãn cho mọi tài liệu.

Công thức: F26. Điểm dễ nhầm: Không phải tỷ lệ relevant của toàn corpus.

Evidence và file/code để mở: src/rag/evaluation.py; reports/rag_v3/retrieval_policy_rows.csv.

### Câu hỏi 43 RAG V3 dùng RRF cho mọi câu hỏi?

Trả lời ngắn: route_query nhận dạng causal, complaint có aspect, general aspect hoặc summary.

Giải thích sâu: build_packet giữ evidence hợp intent/polarity/topic, dedup text và lấy tối đa ba review. Qwen chỉ nhận packet này. attach_citation có thể gắn placeholder bằng overlap khi thiếu inline citation, nhưng sau đó vẫn phải qua validator. Tối đa hai lần sinh; không qua thì extractive_answer, không có evidence thì insufficient.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Aspect complaint dùng BM25 filtered; causal bị guard.

Evidence và file/code để mở: src/rag_v3/routing.py; src/rag_v3/retriever.py; src/rag_v3/evidence.py; src/rag_v3/service.py.

### Câu hỏi 44 E1 khác review ID thế nào?

Trả lời ngắn: Packet chứa question_intent, aspect, restaurant, evidence và aggregates.

Giải thích sâu: frequency_supported=False ngăn suy ra “đa số”, “thường xuyên” từ vài review đã chọn. accepted_review_count đếm evidence sau gate, không phải tổng review của nhà hàng. _packet_text thường lấy 350 ký tự hoặc đoạn quanh complaint cue; đây là truncation bằng ký tự ở packet, khác giới hạn token của embedding.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Placeholder phải map về ID thật, không tự tạo citation.

Evidence và file/code để mở: src/rag_v3/evidence.py::Packet, build_packet, _packet_text, evidence_for_refs.

### Câu hỏi 45 Có citation đúng đã đủ grounded chưa?

Trả lời ngắn: validate_packet_citations kiểm tra inline refs, danh sách refs, aspect/topic, polarity, số ít/số nhiều, frequency language và mixed evidence.

Giải thích sâu: Một câu có review ID đúng vẫn có thể chứa claim không có trong review. Do đó schema và citation validity chưa đủ. Tuy vậy overlap/cue rule cũng có thể bỏ sót hoặc loại nhầm paraphrase; số unsupported accepted bằng 0 là “validator không phát hiện” trong sáu ca, không phải chứng minh không hallucinate trên mọi đầu vào.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Mỗi clause phải được review được dẫn hỗ trợ.

Evidence và file/code để mở: src/rag_v3/evidence.py::validate_packet_citations, _clause_supported; reports/rag_v3/generation_failure_analysis.json.

### Câu hỏi 46 Fallback có được coi là thành công không?

Trả lời ngắn: Khi có packet hợp lệ nhưng hai lần sinh không qua, extractive_answer chọn evidence đầu, trích tối đa khoảng 180 ký tự và gắn ref.

Giải thích sâu: Khi packet rỗng hoặc query causal bị guard, không gọi generation để cố tạo lời giải thích. Trả insufficient-evidence là hành vi đúng cho ba ca thiếu bằng chứng trong nghiệm thu. Fallback không phải crash, nhưng fallback nhiều vẫn cho thấy giới hạn generator; không dùng tỷ lệ answer hợp lệ sau fallback để quảng cáo khả năng synthesis thuần của LLM.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Thành công safety contract nhưng có thể incomplete về nhu cầu.

Evidence và file/code để mở: src/rag_v3/service.py::answer_question_v3; src/rag_v3/evidence.py::extractive_answer.

### Câu hỏi 47 Vì sao demo dùng 3B?

Trả lời ngắn: B biểu thị tỷ tham số xấp xỉ, không phải dung lượng GB.

Giải thích sâu: Trong accepted replay sáu ca, cả hai model có 2 supported complete, 1 supported incomplete, 3 correct insufficient và 0 validator-detected unsupported accepted; fallback giảm từ 3 xuống 2 với 3B. Đây là tín hiệu demo nhỏ để chọn 3B, không phải general LLM ranking. Model file 3B=2.104,932768 MB và 1,5B=1.117,320736 MB; RAM/VRAM còn runtime và context overhead.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Sáu ca là local acceptance nhỏ, không ranking tổng quát.

Evidence và file/code để mở: config/demo.yaml; qwen_v1.yaml; qwen_v3_3b.yaml; reports/rag_v3/generation_metrics.json; reports/task2/FEASIBILITY.csv.

### Câu hỏi 48 DeepSeek thất bại chứng minh nó yếu hơn mọi LLM?

Trả lời ngắn: Ba model dùng cùng sáu saved evidence packets, prompt V3, llama.cpp b11429, temperature=0, seed=42, cap 128 output tokens, không rerun retrieval.

Giải thích sâu: Final gate giữ cùng 2 complete, 1 incomplete, 3 insufficient ở cả ba; Qwen replay mới fallback 3, Llama 2, DeepSeek 3. DeepSeek không tạo schema parseable trong các ca answerable dưới protocol này; không kết luận model nói chung yếu. Qwen replay mới bị contention và chậm hơn accepted replay, nên không trộn hai lần đo.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Khác scale, prompt/schema cap và contention confound.

Evidence và file/code để mở: reports/task2/llm_comparison.csv; reports/task2/llm_benchmark_provenance.json; reports/task2/LLM_BENCHMARK.md.

### Câu hỏi 49 Vì sao latency benchmark LLM rất khác accepted replay?

Trả lời ngắn: Mean là tổng latency chia số quan sát; p95 là percentile 95, phản ánh phần đuôi chậm.

Giải thích sâu: Retrieval latency đo tìm ứng viên; generation latency đo các call hoàn thành; end-to-end gồm retrieval, gate, retries/fallback và overhead. Telemetry cộng usages chỉ của attempts có usage trả về, nên không luôn chứa thời gian timeout. Benchmark còn cột answerable wall time để phản ánh toàn bộ chờ ở các câu có evidence. Mean toàn sáu ca chứa ba refusal nhanh khác mean ba answerable.

Công thức: F27–F28. Điểm dễ nhầm: Khác run, hardware contention và mẫu số đo.

Evidence và file/code để mở: src/rag_v3/service.py; scripts/task2_llm_benchmark.py; reports/task2/FEASIBILITY.csv.

### Câu hỏi 50 GPU layers 99 chứng minh container dùng GPU?

Trả lời ngắn: Model_size_bytes là kích thước file weights trên đĩa; RSS là bộ nhớ resident của process; VRAM là bộ nhớ GPU.

Giải thích sâu: Q4_K_M giảm biểu diễn weights để model chạy trên máy cá nhân, có thể đổi quality. Repository không có đối chứng full precision để tính mất mát do quantization. V1 mất sampler evaluation, chỉ có idle probe riêng; three-family benchmark có sampled RSS nhưng GPU số đo system-wide. Docker nghiệm thu chạy CPU, GPU container NOT VERIFIED dù lệnh yêu cầu gpu layers=99.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Device assignment/runtime capability chưa verified.

Evidence và file/code để mở: reports/proposed_v1/qwen_resource_report.json; reports/task2/llm_comparison.csv; reports/task2/DOCKER_ACCEPTANCE.md.

### Câu hỏi 51 LLMOps có lưu nội dung người dùng không?

Trả lời ngắn: MLOps quản lý data/model version, training evaluation, reproducibility và phục vụ.

Giải thích sâu: record ghi SQLite state/llmops.sqlite với component, timestamp, model hash, prompt version, rag_version, retrieval_method, query_route, evidence_count, support_gate_status, clause_support_status, tokens và latency. safe_filters chỉ giữ restaurant_key, ngày, sentiment, aspect. Không lưu raw question/review trong operational event; intentional evaluation audit riêng có thể lưu raw generation nên không đồng nhất hai nơi.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Operational event không; evaluation audit riêng cần phân biệt.

Evidence và file/code để mở: src/rag/monitoring.py; src/ml/mlflow_tracking.py; src/rag_v3/service.py.

### Câu hỏi 52 Streamlit có gọi API backend cho RAG V3 không?

Trả lời ngắn: Restaurant Intelligence đọc marts, chọn nhà hàng/ngày, hiển thị rating, sentiment, aspect/issues và historical alerts; nút health report gọi V3 health service.

Giải thích sâu: LLMOps Monitor đọc events và report, tách số liệu nghiên cứu với inference demo. Dữ liệu đọc được cache bằng st.cache_data; cache không train lại model. Exception được hiển thị thành trạng thái RAG unavailable để frontend còn đọc dashboard. Đường Analyst hiện tại không gửi HTTP sang rag-backend; sơ đồ chuỗi Streamlit→FastAPI→Qwen sẽ mô tả sai source.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Source gọi V3 modules trực tiếp.

Evidence và file/code để mở: app/app.py::restaurant_page, explorer_page, analyst_page, monitor_page.

### Câu hỏi 53 FastAPI health 200 có chứng minh V3 query thành công?

Trả lời ngắn: API định nghĩa hợp đồng request/response qua HTTP.

Giải thích sâu: /ask hiện import src.rag.service.answer_question và LLMGateway mặc định lịch sử, không dùng answer_question_v3. /health kiểm tra index_manifest và file Qwen v1 1,5B, nên trường qwen_weights_available không phải xác minh model 3B đang serve. Accepted V3 query là đường Streamlit/CLI; tài liệu ghi rõ API là service bổ sung với path legacy, không sửa source trong task documentation.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Endpoint là kiểm cơ bản, /ask còn legacy.

Evidence và file/code để mở: app/api.py; docker-compose.yml; reports/task2/MICROSERVICE_ARCHITECTURE.md.

### Câu hỏi 54 Image container volume khác nhau thế nào?

Trả lời ngắn: Docker đóng gói chương trình và dependency thành image.

Giải thích sâu: Compose gom khai báo service, build, command, ports, mounts và profile trong YAML. Dockerfile.rag dùng Python 3.12 và requirements-demo.txt cho Streamlit/FastAPI; Dockerfile lịch sử dùng Python 3.11 và requirements.txt cho pipeline CLI. Images không mang data/models private; chạy được demo cần mounts có artifact đúng hash.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Mount RW có thể thay file host.

Evidence và file/code để mở: Dockerfile; Dockerfile.rag; docker-compose.yml.

### Câu hỏi 55 Vì sao cài psutil ở đúng requirements mới sửa được?

Trả lời ngắn: Traceback của pipeline là ModuleNotFoundError: No module named 'psutil'.

Giải thích sâu: Fix đã chấp nhận thêm psutil==7.2.2 vào requirements.txt rồi docker compose build pipeline và up -d pipeline. Import probe tải được psutil và src.cli; lệnh --help hoàn tất exit 0. Không chạy ingestion để kiểm tra một lỗi xảy ra ngay lúc import. Task tài liệu này chỉ mô tả fix đã có.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Hai image cài hai dependency sets khác nhau.

Evidence và file/code để mở: requirements.txt; Dockerfile; src/proposed_v1/runtime.py; reports/task2/DOCKER_ACCEPTANCE.md.

### Câu hỏi 56 Pipeline Exited 0 là lỗi hay thành công?

Trả lời ngắn: Pipeline default command là python -m src.cli --help.

Giải thích sâu: docker compose ps thường chỉ hiện service chạy; dùng ps -a để thấy one-shot đã hoàn tất. Qwen có Docker healthcheck thật; backend và Streamlit trong Compose hiện chưa có Docker healthcheck, nhưng HTTP health đã trả 200. Viết “Up và HTTP 200” chính xác hơn gán nhầm trạng thái Docker healthy cho cả ba.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Default command là --help one-shot.

Evidence và file/code để mở: Dockerfile; docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md.

### Câu hỏi 57 CD thành công có phải đã production deploy?

Trả lời ngắn: CI tự động kiểm tra source mới để phát hiện lỗi trước khi tích hợp.

Giải thích sâu: Runtime acceptance local bổ sung phần CI artifact-free không kiểm: weights, Foody index, Qwen health, real query và LLMOps event. Hai nhóm evidence trả lời hai câu hỏi khác nhau: source/image có build được, và artifact-mounted demo có thực thi được.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Chỉ publication image; remote deployment ngoài scope.

Evidence và file/code để mở: .github/workflows/ci.yml; .github/workflows/release.yml; reports/task2/DOCKER_ACCEPTANCE.md.

### Câu hỏi 58 Release mới nhất nào đã được xác minh?

Trả lời ngắn: GHCR là registry lưu image layers và manifests; URL ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 chỉ một image reference.

Giải thích sâu: CI run 39739640437 và release run 39742439011 đều success tại commit 4229a8b3998392c97f4b7a8c9e3795830285dbce. Đây là cập nhật mới hơn CICD_EVIDENCE.md còn nhắc v1.0.0. Tài liệu lưu kiểm tra read-only ngày 22/10/2026; không sửa workflow hoặc phát hành image mới.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: v1.0.1 ở 4229a8b; docs mới chưa nằm trong CI đó.

Evidence và file/code để mở: public GitHub Actions run URLs trong Evidence Map; docker buildx imagetools inspect v1.0.1 tại audit.

### Câu hỏi 59 24 trên 24 DONE có nghĩa không còn limitation?

Trả lời ngắn: Giới hạn dữ liệu: label aspect-level có xung đột text-only; neutral ít; Foody không có gold labels; tên nhà hàng chưa là ID chính thức; sampling review có thiên lệch.

Giải thích sâu: Giới hạn RAG: sáu query với relevance chưa đầy đủ, truncation embedding dài, rule support không phải human entailment, latency khác run/hardware và generator fallback nhiều. Ablation là observed progression, không có packet-off/validator-off/fallback-off controls. GPU Docker chưa được xác minh; không train LLM from scratch; CD không phải remote production deployment.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Checklist evidence hoàn tất không xóa scientific caveats.

Evidence và file/code để mở: reports/task2/TRAINING_SCOPE.md; reports/task2/LLM_BENCHMARK.md; reports/task2/CHUNKING_DECISION.md.

### Câu hỏi 60 Task tiếp theo nên ưu tiên gì?

Trả lời ngắn: Giới hạn dữ liệu: label aspect-level có xung đột text-only; neutral ít; Foody không có gold labels; tên nhà hàng chưa là ID chính thức; sampling review có thiên lệch.

Giải thích sâu: Giới hạn RAG: sáu query với relevance chưa đầy đủ, truncation embedding dài, rule support không phải human entailment, latency khác run/hardware và generator fallback nhiều. Ablation là observed progression, không có packet-off/validator-off/fallback-off controls. GPU Docker chưa được xác minh; không train LLM from scratch; CD không phải remote production deployment.

Công thức: Không áp dụng phép tính riêng; xem logic source. Điểm dễ nhầm: Đánh giá độc lập tốt hơn trước khi tăng complexity.

Evidence và file/code để mở: reports/task2/TRAINING_SCOPE.md; reports/task2/LLM_BENCHMARK.md; reports/task2/CHUNKING_DECISION.md.

## Chương 85 Cheat sheet trình bày và vận hành

Năm trang tra cứu cuối chương gom số liệu, model, luồng chạy, lệnh và giới hạn. Sử dụng như bảng nhắc khi demo; các chương trước và notebook tính toán là nơi giải thích chi tiết. Những lệnh train/index chỉ xuất hiện như mô tả nghiên cứu, không phải yêu cầu chạy lại demo.
Nguồn: README.md; config/demo.yaml; reports/task2/; scripts/start_demo.ps1.

<!-- PAGEBREAK -->

### Trang tra cứu 1 Số liệu

Research 5869 rows; 1530 review IDs; 5316 texts. Split4140/842/887; class positive3714 negative1861 neutral294. Foody33946 raw,33938 valid,31694 observations,32457 valid distinct reviews,2110 restaurants. RAG32457 document/vector/BM25. Không nhầm row với group; xem reports/food_dataset_report.json và reports/foody_intelligence/cleaning.json.

Bảng 35. Split và số đếm

| Split | Rows | Review IDs | Negative | Neutral | Positive |
| --- | --- | --- | --- | --- | --- |
| train | 4140 | 1074 | 1307 | 208 | 2625 |
| validation | 842 | 229 | 270 | 43 | 529 |
| test | 887 | 227 | 284 | 43 | 560 |

Nguồn: data/food/splits/metadata.json. Loại: MEASURED.

Bảng 36. Các đơn vị đếm Foody

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

<!-- PAGEBREAK -->

### Trang tra cứu 2 Models và metrics

TF-IDF LR text-only: accuracy0.809470 macro-F1 0.682854 neutral-F1 0.413043. Rule macro0.431279; QwenV1 macro0.621789; V2-A macro0.614487 exploratory. Aspect micro0.832277 macro0.633628 trên797 grouped texts. MiniLM384D CPU ONNX; Qwen3B Q4_K_M cho RAG. Nguồn: baseline/V1/V2/aspect metrics, config/demo.yaml.

Bảng 37. Research results

| Model | Accuracy | Macro F1 | Weighted F1 |
| --- | --- | --- | --- |
| Rule-based | 0.505073 | 0.431279 | 0.592298 |
| TF-IDF + Logistic Regression | 0.809470 | 0.682854 | 0.812104 |
| TF-IDF + LinearSVC | 0.818489 | 0.667210 | 0.814830 |

Nguồn: reports/task2/classical_model_comparison.csv. Loại: MEASURED.

<!-- PAGEBREAK -->

### Trang tra cứu 3 RAG và thuật ngữ

Complaint+aspect → filtered BM25/rerank; general→RRF; causal→guard. Top-k5; candidate20/nhánh; RRF60; packet≤3 reviews; 350 ký tự/evidence; output cap128; attempts2. Schema→citation→clause validation→extractive/insufficient. Historical Hit columns = KP recall. Nguồn: src/rag_v2/hybrid.py; src/rag_v3/.

Trước khi trả lời: đúng restaurant? đúng date? đúng aspect/polarity? đủ evidence? claim có frequency/causality không? refs có map đúng? fallback đã hiển thị chưa? Đây là checklist giải thích logic hiện có, không thêm guard mới.

<!-- PAGEBREAK -->

### Trang tra cứu 4 Vận hành

Local .\scripts\start_demo.cmd chạy preflight, Qwen3B8194 và UI8501; -CpuOnly fallback. Compose Qwen8193, API8000, UI8501; pipeline help exit0. models/reports RO; data/state RW. CI39739640437 và release39742439011 success, tagv1.0.1, commit4229a8b. Không chạy train/index để demo. Nguồn: docker-compose.yml; scripts/start_demo.ps1; public CI/CD audit.

```powershell
.\.venv\Scripts\python.exe -m src.cli demo-preflight
.\scripts\start_demo.cmd
docker compose config --quiet
docker compose ps -a
```

<!-- PAGEBREAK -->

### Trang tra cứu 5 Giới hạn và bảo vệ

24/24 checklist là hoàn tất evidence, không production certification. Sáu RAG queries, incomplete relevance; no Foody gold; heuristic issues/support; zero-support amenities/room; embedding truncation; GPU Docker NOT VERIFIED; no LLM pretraining; CD chỉ publish. N/A phải giữ N/A. Source hiện tại thắng old prose; xem DOCUMENTATION_AUDIT.md để đối chiếu mâu thuẫn.

<!-- PAGEBREAK -->

## Phụ lục A Công thức và phép tính

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

## Phụ lục B Code to math traceability

Bảng 38. Trace công thức đến implementation

| Concept / formula | Function | Input → output evidence |
| --- | --- | --- |
| F01 Imbalance ratio | Không có function model; phép tính documentation | reports/task2/class_distribution.csv |
| F02 Balanced class weights | src/baselines/tfidf_logreg.py::build_pipeline | reports/task2/imbalance_comparison.csv |
| F03 Term frequency | TfidfVectorizer(sublinear_tf=True) | src/baselines/tfidf_logreg.py |
| F04 Smoothed IDF | TfidfVectorizer(smooth_idf=True mặc định) | src/baselines/tfidf_logreg.py; sklearn API |
| F05 TF IDF và L2 | TfidfVectorizer(norm='l2' mặc định) | src/baselines/tfidf_logreg.py |
| F06 Logistic sigmoid | OneVsRestClassifier(LogisticRegression) | src/foody/aspect.py |
| F07 Multinomial softmax | LogisticRegression(solver='lbfgs') | src/baselines/tfidf_logreg.py |
| F08 Accuracy thật từ confusion | src/baselines/metrics.py::scores → accuracy_score | reports/baselines/tfidf_test_metrics.json |

Nguồn: source code cited in từng dòng. Loại: SOURCE AUDIT.

Bảng 39. Trace công thức đến implementation

| Concept / formula | Function | Input → output evidence |
| --- | --- | --- |
| F09 Neutral precision | src/baselines/metrics.py::class_report | reports/baselines/tfidf_test_metrics.json |
| F10 Neutral recall | precision_recall_fscore_support | reports/baselines/tfidf_test_metrics.json |
| F11 Neutral F1 | src/baselines/metrics.py::scores | reports/baselines/tfidf_test_metrics.json |
| F12 Macro F1 | precision_recall_fscore_support(average='macro') | reports/baselines/tfidf_test_metrics.json |
| F13 Weighted F1 | precision_recall_fscore_support(average='weighted') | reports/baselines/tfidf_test_metrics.json |
| F14 Micro F1 và exact match | precision_recall_fscore_support; accuracy_score | src/foody/aspect.py::scores |
| F15 Stride | policy_measure | scripts/task2_rag_accounting.py::policy_measure |
| F16 Số chunk | policy_measure | scripts/task2_rag_accounting.py |

Nguồn: source code cited in từng dòng. Loại: SOURCE AUDIT.

Bảng 40. Trace công thức đến implementation

| Concept / formula | Function | Input → output evidence |
| --- | --- | --- |
| F17 Corpus token average | scripts/task2_rag_accounting.py::summary | reports/task2/rag_token_statistics.json |
| F18 Raw vector payload | LocalEmbeddings._embed(dtype=float32) | src/rag/embeddings.py; Chroma manifest |
| F19 Binary Hit at k | Chưa có binary Hit function trong accepted evaluation | src/rag/evaluation.py đối chiếu semantics |
| F20 Known-positive recall at k | known_positive_scores | src/rag/evaluation.py::known_positive_scores |
| F21 Mean và sample standard deviation | scripts/task2_finalize_evidence.py; statistics.stdev trong docs | reports/task2/baseline_three_seed.csv |
| F22 Improvement signals | documentation arithmetic | reports/proposed_v1/qwen_test_metrics.json; baseline JSONs |
| F23 Embedding throughput và simulation | scripts/task2_rag_accounting.py | reports/task2/embedding_workload.csv |
| F24 RRF | rrf_fuse | src/rag_v2/hybrid.py::rrf_fuse |

Nguồn: source code cited in từng dòng. Loại: SOURCE AUDIT.

Bảng 41. Trace công thức đến implementation

| Concept / formula | Function | Input → output evidence |
| --- | --- | --- |
| F25 BM25 | SQL bm25(reviews_fts) | src/rag_v2/lexical.py; SQLite documentation |
| F26 Mean reciprocal rank | known_positive_scores | src/rag/evaluation.py::known_positive_scores |
| F27 Mean latency | measure_predictions; telemetry | src/baselines/metrics.py; src/rag_v3/service.py |
| F28 Percentile p95 | np.percentile / Series.quantile | src/baselines/metrics.py; numpy/pandas default |
| F29 Review vượt 128 tokens | scripts/task2_rag_accounting.py::policy_measure | reports/task2/chunking_comparison.csv |
| F30 V1 test token usage | src/proposed_v1/runner.py::usage | reports/proposed_v1/qwen_test_metrics.json |

Nguồn: source code cited in từng dòng. Loại: SOURCE AUDIT.

## Phụ lục C Lệnh tái lập và vận hành

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

## Phụ lục D Evidence và source map

Bảng 42. Evidence Map 1

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

Bảng 43. Evidence Map 2

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

Bảng 44. Evidence Map 3

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

Bảng 45. Evidence Map 4

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

Bảng 46. Evidence Map 5

| Claim | Value | Type / verified | Evidence |
| --- | --- | --- | --- |
| Tests | 288 passed / 1 warning | MEASURED / Có | reports/task2/REVIEW2_STATUS_SUMMARY_VI.md |
| CI | 39739640437 success at 4229a8b | MEASURED / Có | https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39739640437 |
| CD release | 39742439011 success v1.0.1 | MEASURED / Có | https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39742439011 |
| GHCR manifest | sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a | MEASURED / Có | ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 |

Nguồn: source paths trong từng dòng. Loại: MIXED.

## Phụ lục E Mâu thuẫn tài liệu và quyết định xử lý

### KEY_NUMBERS ai_valid_count

Phát hiện: 31694 bị dùng như số dòng AI hợp lệ. Kết luận dùng trong tài liệu: 33938 valid source rows; 31694 inference observations; 32457 distinct valid reviews. Nguồn: src/foody/cleaning.py; reports/foody_intelligence/cleaning.json.

### Hit@5/10 labels

Phát hiện: Tên Hit nhưng formula chia cho số known positives. Kết luận dùng trong tài liệu: Giữ số gốc, ghi macro known-positive recall; binary Hit định nghĩa riêng. Nguồn: src/rag/evaluation.py; scripts/evaluate_rag_v3_retrieval.py.

### V2-A input

Phát hiện: GAP_ANALYSIS/Q&A cũ gọi aspect-conditioned. Kết luận dùng trong tài liệu: V2-A text-only; V2-B ở src/aspect_conditioned là text+aspect. Nguồn: qwen_v2.yaml; qwen_aspect.yaml; reports/proposed_v2/protocol.json.

### Docker trạng thái cũ

Phát hiện: FINAL_ARCHITECTURE/Q&A ghi daemon chưa chạy. Kết luận dùng trong tài liệu: DOCKER_ACCEPTANCE mới xác minh serving + pipeline exit0. Nguồn: reports/task2/DOCKER_ACCEPTANCE.md.

### CI/CD trạng thái cũ

Phát hiện: CICD_EVIDENCE mới nhất trong repo vẫn dừng v1.0.0. Kết luận dùng trong tài liệu: Public API và registry xác nhận v1.0.1 tại 4229a8b; docs chưa nằm trong run đó. Nguồn: GitHub CI 39739640437; release 39742439011; GHCR digest.

### Test count

Phát hiện: KEY_NUMBERS ghi 287. Kết luận dùng trong tài liệu: Kết quả gần nhất 288 passed 1 warning, không chạy lại trong task docs. Nguồn: reports/task2/REVIEW2_STATUS_SUMMARY_VI.md; phiên acceptance trước.

### Luồng UI API

Phát hiện: Sơ đồ gợi ý UI→API→Qwen. Kết luận dùng trong tài liệu: UI V3 gọi Python trực tiếp; API /ask là legacy parallel service. Nguồn: app/app.py; app/api.py.

### Qwen port/model

Phát hiện: Config v1 và health API trỏ 1.5B; 3B local port8194. Kết luận dùng trong tài liệu: Streamlit selected_v3_gateway dùng 3B; Compose URL override port8193. Nguồn: config/demo.yaml; qwen_v3_3b.yaml; docker-compose.yml.

### Latency RAG

Phát hiện: Các bảng có số khác nhau theo run. Kết luận dùng trong tài liệu: Tách shared policy run, V2 candidates, accepted replay, three-family replay và Docker CPU. Nguồn: reports/rag_v3/retrieval_policies.csv; reports/task2/FEASIBILITY.csv.

### Embedding chọn model

Phát hiện: Một số mô tả dễ hiểu thành chưa từng benchmark. Kết luận dùng trong tài liệu: Có 2-model pool612 comparison; chưa exhaustive benchmark. Nguồn: reports/rag/embedding_comparison.csv.

### GPU configuration

Phát hiện: gpu_layers=99 dễ bị coi là GPU verified. Kết luận dùng trong tài liệu: Requested khác observed; Docker CPU, GPU NOT VERIFIED. Nguồn: reports/task2/DOCKER_ACCEPTANCE.md.

### Causal mart guard

Phát hiện: Tên policy dễ hiểu là causal analysis từ mart. Kết luận dùng trong tài liệu: Query route trả no hits/insufficient; không ước lượng causal effect. Nguồn: src/rag_v3/retriever.py; src/rag_v3/evidence.py.

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
