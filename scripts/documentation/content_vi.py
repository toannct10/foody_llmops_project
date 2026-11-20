"""Vietnamese explanatory prose for documentation only; no runtime imports."""

CHAPTERS = r"""
@@1|Bài toán và giá trị sử dụng
Người quản lý nhà hàng cần biết khách đang khen hoặc phàn nàn điều gì, tại chi nhánh nào và trong khoảng thời gian nào. Khi hàng nghìn nhận xét nằm rải rác trong file xuất, đọc từng dòng khó tạo được một bức tranh nhất quán. Hệ thống chuẩn hóa dữ liệu, bổ sung dự đoán sentiment và aspect, tạo bảng tổng hợp, rồi cho phép hỏi bằng tiếng Việt với bằng chứng review đi kèm.

Có hai luồng độc lập. VN-MSASar cung cấp nhãn nghiên cứu để huấn luyện và đánh giá classifier; Foody là dữ liệu thực tế để suy luận, dashboard và RAG. Kết quả tốt trên VN-MSASar không tự biến thành accuracy trên Foody. Sản phẩm là demo chạy local đã nghiệm thu, chưa có bằng chứng triển khai production từ xa.

Luồng nghiệp vụ: Review → kiểm tra và làm sạch → sentiment → aspect → issue heuristic → restaurant marts và tài liệu RAG → truy xuất → evidence packet → LLM → kiểm tra căn cứ → Streamlit. Người dùng thấy cả chế độ trả lời và nguồn trích dẫn để đánh giá mức chắc chắn.
Nguồn: README.md; src/foody/pipeline.py; app/app.py; reports/task2/TRAINING_SCOPE.md.
@@2|Lịch sử phát triển và quyết định qua từng giai đoạn
Hướng ban đầu là Shopee crawler và Databricks. Những module còn tồn tại phục vụ kiểm thử và audit lịch sử, không phải đường demo hiện hành. Cần ghi đúng: Historical experiment — not current production path. Repository sau đó chuyển sang review nhà hàng Việt Nam và đóng băng dataset trước khi so sánh phương pháp.

Baseline rule kiểm tra mức có thể đạt bằng từ điển thủ công. TF-IDF LR học mẫu từ/cụm từ từ train và vượt rule. Giả thuyết LLM prompt có thể tốt hơn được thử ở Qwen V1; kết quả macro-F1 thấp hơn TF-IDF dẫn đến V2-A hiệu chỉnh prompt. V2-A không cải thiện; nghiên cứu text+aspect là V2-B riêng, cũng không thay thế classifier đã chọn.

Đối với demo, vấn đề chuyển sang tìm và diễn đạt bằng chứng. RAG V1 dùng dense; V2 bổ sung BM25, RRF và quy tắc evidence; V3 định tuyến, chuẩn bị packet trước sinh và có fallback. Streamlit trình bày dữ liệu, LLMOps ghi vận hành; Docker và CI/CD xác minh khả năng đóng gói. Chuỗi này là tiến trình đổi bài toán và rút kinh nghiệm, không phải một bảng accuracy liên tục từ sentiment sang RAG.
Nguồn: reports/final/TASK2_EXPERIMENT_STORY.md; docs/experiments/; reports/task2/RAG_ABLATION_FINAL.md.
@@3|Dataset VN MSASar v3
Nguồn public là phamluan/vn_msa_sar_v3 trên Hugging Face, revision 6f3f17b390dcf1bf411804e1bc8246bf88ea1bf4, license CC BY 4.0 theo provenance. Ba file nguồn có tổng 76.785 dòng. Adapter chỉ giữ language=vi và place_type=restaurant, còn 5.869 dòng hợp lệ; không có dòng bị reject hoặc duplicate bị loại ở lần chuẩn bị đã lưu.

Một dòng biểu diễn câu và aspect được gán nhãn, không nhất thiết là một review độc lập. Có 1.530 review_id và 5.316 câu chuẩn hóa riêng biệt. Schema nguồn gồm review_id, source, place_type, language, sentence, aspect, sentiment, sarcasm. Adapter đổi sentence thành text, giữ original_text và original_sentiment, lưu metadata provenance. research source=foody không có nghĩa là cùng export Foody first-party dùng cho demo.

Hãy đọc bảng phân bố phía dưới cùng đơn vị đếm. food xuất hiện nhiều vì mỗi dòng mang một aspect; aspect classifier sau này gộp những dòng có cùng text thành target nhiều nhãn. Không cộng số research rows với RAG documents thành một tập train chung.
Nguồn: reports/food_dataset_report.json; src/food/adapters.py; data/food/source/vn_msasar_v3/provenance.json.
@@4|Chuẩn hóa nhãn cảm xúc
Thang sentiment nguồn là số nguyên từ −3 đến +3. Hàm ordinal kiểm tra số hữu hạn, nguyên và nằm trong tập cho phép; boolean, NaN hoặc giá trị ngoài miền bị loại. LABEL_MAPPING ánh xạ số âm thành negative, 0 thành neutral và số dương thành positive. Đây là phép gộp độ mạnh theo dấu, không phải chuyển rating sao thành sentiment.

THEORY: negative biểu đạt không hài lòng; positive biểu đạt hài lòng; neutral là trung tính theo nhãn nguồn. EXAMPLE: −2 và −1 cùng trở thành negative, +1 và +3 cùng positive. PROJECT RESULT: original_sentiment được giữ để truy vết; ba nhãn được dùng nhất quán trong metrics. Gộp nhãn làm bài toán đơn giản hơn nhưng mất thông tin cường độ và vẫn không giải quyết câu có cảm xúc khác nhau theo aspect.
Nguồn: src/food/adapters.py::ordinal và LABEL_MAPPING; reports/food_label_mapping.json.
@@5|Train validation test và kiểm soát leakage
Train dùng để fit vocabulary, IDF và trọng số classifier. Validation chọn cấu hình/prompt. Test chỉ đánh giá cấu hình đã đóng băng. Đưa một phần câu test vào quá trình fit làm mô hình biết trước đặc điểm tập đánh giá và tạo ước lượng lạc quan.

assign_splits không chia từng dòng độc lập: leakage_groups dùng thành phần liên thông nối các dòng chung review_id hoặc text chuẩn hóa. Vì thế một review hoặc câu giống hệt không đi vào nhiều split. Thuật toán tìm 64 phương án GroupShuffleSplit theo seed 42 rồi chọn phương án gần tỷ lệ và phân bố lớp mong muốn; đây là tìm split bằng nhãn, không phải chọn theo điểm dự đoán test. Tỷ lệ thực không đúng tuyệt đối 70/15/15 do ràng buộc nhóm.

PROJECT RESULT: 4.140 train, 842 validation, 887 test; tương ứng 1.074, 229, 227 review IDs. Có 1.481 thành phần liên thông. Kiểm tra ID và normalized text giao nhau đều bằng 0; near-duplicate gần giống chưa được đảm bảo. V2 và ba-seed dùng lại test đã nhìn thấy phải mang nhãn exploratory.
Nguồn: src/food/split.py::leakage_groups, assign_splits, load_splits; data/food/splits/metadata.json.
@@6|Mất cân bằng lớp
Positive chiếm 3.714 dòng, negative 1.861 và neutral 294. Class imbalance nghĩa là số ví dụ giữa các lớp chênh lệch; mô hình có thể ưu tiên lớp đông và vẫn có accuracy khá. Vì thế macro-F1, lấy trung bình công bằng theo lớp, phù hợp để chọn sentiment classifier trong project.

DERIVED: imbalance ratio = 3.714 / 294 = 12,632653. Neutral chiếm 294 / 5.869 × 100 = 5,009371%. Tỷ lệ này mô tả toàn bộ tập nghiên cứu, không phải weight tính khi train. Class weighting không thay đổi biểu đồ số dòng nên không có một phân bố sample sau cân bằng mới.
Nguồn: reports/task2/class_distribution.csv; reports/food_dataset_report.json.
@@7|Class weight và lý do không dùng SMOTE
Balanced weight tăng chi phí của lỗi ở lớp ít ví dụ. Với N=4.140 và K=3, weight_j=N/(K×n_j). Train negative=1.307 cho weight 1,055853; neutral=208 cho 6,634615; positive=2.625 cho 0,525714. Các giá trị được tính lại bằng script tài liệu, không chỉnh training.

Validation cho thấy neutral recall tăng từ 0,093023 lên 0,488372 và neutral F1 tăng từ 0,170213 lên 0,471910 khi dùng balanced. Precision neutral giảm từ 1 xuống 0,456522: mô hình tìm thêm neutral nhưng cũng tạo false positives. Đây là trade-off có đo đạc, không phải lời khẳng định mọi lớp đều tốt hơn.

SMOTE không được dùng. Nội suy vector TF-IDF sparse không tương đương tạo review tiếng Việt tự nhiên, còn weighting tác động trực tiếp hàm mất mát và giữ nguyên membership. Repository không có thử nghiệm SMOTE đối chứng, nên không kết luận SMOTE chắc chắn kém hơn.
Nguồn: src/baselines/tfidf_logreg.py; reports/task2/imbalance_comparison.csv.
@@8|Foody và ý nghĩa từng loại số đếm
Nguồn demo hiện hành là data/foody/source/foody_reviews.csv, không phải review.csv lịch sử. First-party ownership là thông tin người dùng cung cấp; checksum chỉ chứng minh snapshot trùng byte, không tự chứng minh quyền sở hữu hoặc tính đại diện. Có 33.946 dòng thô, 33.938 dòng hợp lệ cho AI, 31.694 observation suy luận sau gộp và 32.457 review_id hợp lệ riêng biệt, thuộc 2.110 restaurant_key.

Một observation gộp restaurant_key với text chuẩn hóa để tránh dự đoán lặp. Một review_id còn gồm User, thời gian thô và Comment gốc, vì vậy các người/ngày khác nhau có thể chia sẻ một lần suy luận nhưng vẫn là review khác. Marts/RAG dùng distinct review_id; processed/enriched giữ tất cả source rows. restaurant_key tạo từ tên chuẩn hóa, không phải official ID; trùng tên chi nhánh vẫn là rủi ro.

Ngày nguồn từ 2011-01-09 12:07:32 đến 2026-10-14 15:46:56, rating 0–10. Một comment rỗng và bảy comment chứa U+FFFD bị loại khỏi AI, không sửa đoán chữ. Dấu hỏi kép là cờ chẩn đoán, không tự động là lỗi encoding. Export hiện hành không có Classification và không có sentiment/aspect gold đáng tin cậy; mọi nhãn bổ sung là dự đoán.
Nguồn: src/foody/cleaning.py; src/foody/schema.py; reports/foody_intelligence/cleaning.json.
@@9|Data marts phục vụ quản lý nhà hàng
Data mart là bảng đã tổng hợp cho một câu hỏi nghiệp vụ. restaurant_summary cho số review, rating trung bình và tỷ lệ sentiment; restaurant_daily_metrics và restaurant_monthly_metrics thêm trục thời gian; restaurant_aspect_summary và restaurant_issue_summary cho phân bố nhãn dự đoán; alerts giữ các thay đổi vượt ngưỡng.

business_rows loại trùng review_id trước tổng hợp. Mẫu số của sentiment là review hợp lệ có prediction; mẫu số rating chỉ gồm numeric rating trong [0,10]. Complaint rate kết hợp overall negative và aspect presence, không phải xác suất aspect-level sentiment gold. Một review nhiều aspect có thể đóng góp vào nhiều tỷ lệ, nên không buộc tổng tỷ lệ aspect bằng 100%.

alerts so sánh hai tháng lịch liền kề với ít nhất 10 mẫu mỗi kỳ, chênh tỷ lệ ≥0,2 hoặc rating giảm ≥1,0. Tháng cuối bị bỏ khỏi so sánh vì có thể chưa đủ tháng. Các ngưỡng là engineering choice, chưa có tối ưu có kiểm soát. Đây là cảnh báo lịch sử, không chứng minh nguyên nhân suy giảm hay tình trạng hiện tại.
Nguồn: src/foody/analytics.py; reports/foody_intelligence/mart.json.
@@10|Sentiment analysis từ đầu
Sentiment analysis ánh xạ văn bản sang thái độ cảm xúc. Trong bài toán này một text chỉ nhận một trong ba nhãn negative, neutral, positive. Các từ ngon, tệ có thể là tín hiệu, nhưng phủ định, mỉa mai, ngữ cảnh và câu nhiều ý làm quan hệ từ–nhãn không đơn giản.

EXAMPLE: “Món ngon nhưng phục vụ chậm” chứa khen food và chê service. Nếu chỉ đưa text, mô hình không biết người đánh giá muốn sentiment của aspect nào. PROJECT RESULT: có 81 normalized texts mang gold sentiment xung đột toàn tập, 11 trong test. Đây là giới hạn thông tin của protocol text-only, không thể sửa bằng đổi nhãn cho thuận lợi.
Nguồn: src/baselines/runner.py; reports/baselines/failure_analysis_summary.json; reports/task2/GAP_ANALYSIS.md.
@@11|Baseline rule based
VietnameseRuleBased tách token và dấu câu; khớp cụm lexicon dài nhất không chồng lấp. Từ/cụm tích cực đóng góp +1, tiêu cực −1. Số lượng phủ định lẻ trong ba token trước đảo dấu; punctuation hoặc từ đối lập kết thúc phạm vi. Intensifier nhân đóng góp với 1,5. Tổng dương → positive, âm → negative, bằng 0 → neutral.

EXAMPLE: “không ngon” đảo tín hiệu ngon thành âm. “rất ngon nhưng chậm” có thể cộng 1,5 và −1, ra positive: đó là hành vi của quy tắc, không bảo đảm đúng nhãn aspect. Rule không học trọng số và không đọc gold, rating hoặc aspect. Nó dễ giải thích và nhanh nhưng thiếu từ vựng, thành ngữ và sarcasm.

PROJECT RESULT: accuracy 0,505073; macro-F1 0,431279; neutral recall cao nhưng precision thấp do nhiều câu không khớp lexicon rơi về neutral. Đây là baseline tham chiếu thấp, không phải thuật toán được tái lập từ một paper có cùng split.
Nguồn: src/baselines/rule_based.py; reports/baselines/rule_based_test_metrics.json.
@@12|TF IDF và biểu diễn văn bản
TF-IDF chuyển câu thành vector mà mỗi chiều ứng với một token hoặc n-gram trong vocabulary train. TF phản ánh tần suất trong văn bản; IDF giảm trọng số từ xuất hiện trong nhiều văn bản. Vector sparse lưu chủ yếu giá trị khác 0, phù hợp câu ngắn và vocabulary lớn.

THEORY: cách giới thiệu phổ biến dùng TF=count/độ dài và IDF=ln(N/df). PROJECT CONFIG: TfidfVectorizer dùng sublinear_tf=True nên TF=1+ln(count) khi count>0; smooth_idf mặc định cho IDF=ln((1+N)/(1+df))+1, sau đó chuẩn hóa L2. Không được lấy công thức TF chuẩn hóa độ dài làm mô tả chính xác implementation.

EXAMPLE: “món ăn rất ngon nhưng phục vụ chậm” cho unigram món, ăn, rất... và bigram món ăn, ăn rất, rất ngon... Token pattern cho phép cả từ một ký tự; không có word segmentation tiếng Việt chuyên biệt. Bigrams giúp giữ một phần ngữ cảnh nhưng tăng vocabulary; IDF chỉ fit trên train.
Nguồn: src/baselines/tfidf_logreg.py::build_pipeline; tài liệu TfidfVectorizer scikit-learn 1.7.
@@13|Các tham số TF IDF và bằng chứng lựa chọn
Ba trial thật là unigram C=1, unigram+bigram C=1 và unigram+bigram C=2. Validation macro-F1 lần lượt 0,648722; 0,700294; 0,709242. Trial thứ ba được chọn theo max validation macro-F1; stable candidate order xử lý hòa. Đây là bằng chứng lựa chọn trong tập ba ứng viên, không phải chứng minh tối ưu toàn bộ không gian.

max_features=20.000 giới hạn vocabulary, min_df=2 bỏ token xuất hiện trong ít hơn hai document train, sublinear_tf=True giảm ưu thế từ lặp. max_iter=1.500 là trần solver, lbfgs là solver sentiment, random_state=42 cố định protocol. Các giá trị này không có sweep độc lập trong repo. Tăng vocabulary có thể giữ tín hiệu hiếm nhưng tăng kích thước và overfit; tăng min_df giảm nhiễu nhưng có thể mất slang hiếm.

Engineering/configuration choice; repository hiện không có controlled experiment đủ để chứng minh đây là giá trị tối ưu. Câu này áp dụng cho từng tham số cố định chưa có đối chứng, không áp dụng thay cho bảng trial n-gram/C đã có.
Nguồn: reports/baselines/tfidf_experiments.csv; src/baselines/tfidf_logreg.py.
@@14|Logistic Regression
Một classifier tuyến tính tính score z=wᵀx+b. x là vector TF-IDF; w học từ train; b là bias. Với hai lớp, sigmoid đổi score thành xác suất. Với ba lớp của sentiment và solver lbfgs ở scikit-learn 1.7.2, cách giải thích đúng là multinomial softmax: mỗi lớp có score riêng, rồi exp(score) được chuẩn hóa bằng tổng exp của mọi lớp.

Training tối ưu hàm mất mát có regularization và class weights. predict chọn lớp có xác suất lớn nhất, predict_proba cung cấp vector xác suất. Decision boundary là nơi score của hai lớp bằng nhau. Các xác suất này chưa được calibration trên Foody; giá trị 0,9 không tự chứng minh 90% đúng trong miền dữ liệu mới.

Aspect classifier là trường hợp khác: OneVsRest tạo bài toán nhị phân độc lập cho từng aspect với solver liblinear và threshold. Không trộn softmax của sentiment với sigmoid của OVR.
Nguồn: src/baselines/tfidf_logreg.py; src/foody/aspect.py; tài liệu LogisticRegression scikit-learn 1.7.
@@15|Regularization và C
Regularization hạn chế nghiệm quá phụ thuộc các mẫu train. C là nghịch đảo mức regularization: C nhỏ phạt trọng số mạnh hơn, C lớn cho phép fit linh hoạt hơn. Không diễn giải C=2 là learning rate hay số lớp. Penalty mặc định của cấu hình đang dùng là L2.

PROJECT RESULT: trong cặp cùng bigram, đổi C=1 sang 2 tăng validation macro-F1 từ 0,700294 lên 0,709242. Chỉ có bằng chứng cho hai điểm đó; không suy ra C=10 sẽ tốt hơn. Mô hình được fit train rồi chọn bằng validation, không refit train+validation trước test trong protocol đã lưu.
Nguồn: src/baselines/runner.py; reports/baselines/tfidf_experiments.csv; reports/baselines/tfidf_selection.json.
@@16|Metrics và đọc confusion matrix
Confusion matrix có hàng là gold và cột là predicted. Với một lớp đang xét, TP là đúng lớp đó; FP là lớp khác bị dự đoán thành nó; FN là lớp đó bị bỏ sót. Accuracy đếm đúng trên tổng; precision hỏi “những dự đoán lớp này đáng tin đến đâu”; recall hỏi “tìm được bao nhiêu ví dụ thực của lớp này”. F1 là trung bình điều hòa precision/recall.

Macro-F1 lấy trung bình F1 từng lớp, không phải F1 tính từ macro-precision và macro-recall. Weighted-F1 dùng support làm trọng số nên lớp positive đông có ảnh hưởng lớn. Micro-F1 gom TP/FP/FN trước khi tính; trong single-label đủ nhãn nó bằng accuracy, nhưng trong multi-label không còn như vậy. zero_division=0 xử lý mẫu số bằng 0 trong code.

EXAMPLE: ma trận minh họa và tính tay nằm trong phụ lục công thức; được ghi rõ không phải kết quả project. PROJECT RESULT: confusion TF-IDF thật được đọc trực tiếp từ JSON để tính lại accuracy, precision, recall và F1, không chạy lại model.
Nguồn: src/baselines/metrics.py::scores, class_report; reports/baselines/tfidf_test_metrics.json.
@@17|Kết quả baseline và chọn classifier triển khai
Rule-Based đạt test accuracy 0,505073, macro-F1 0,431279. TF-IDF LR đạt 0,809470 và 0,682854. TF-IDF neutral F1 là 0,413043, vẫn yếu hơn negative/positive. Accuracy cao hơn chưa đủ; macro-F1 và per-class report xác nhận cải thiện có ý nghĩa đối với mục tiêu ba lớp.

Classifier TF-IDF được dùng trong Foody inference vì kết quả đã đo tốt hơn Qwen V1 cho phân loại text-only, latency trung bình single-sample 0,365186 ms và artifact 0,342442 MB. Các timing này là run local riêng, không phải SLA production hoặc speedup đối chứng trên mọi thiết bị. Qwen đảm nhiệm sinh câu từ bằng chứng, một năng lực khác với gán nhãn.
Nguồn: reports/baselines/baseline_comparison.csv; reports/task2/FEASIBILITY.csv; src/foody/enrichment.py.
@@18|Độ ổn định ba seed
Seed điều khiển các bước ngẫu nhiên; không phải mọi solver đều nhạy với seed. Ba lần train so sánh dùng seed 42, 123, 2026 trên cùng frozen membership và cùng cấu hình đã chấp nhận. Artifact classifier demo không bị ghi đè bởi nghiên cứu này.

PROJECT RESULT: cả ba có test macro-F1 0,682854, accuracy 0,809470, weighted-F1 0,812104 và neutral F1 0,413043; sample SD bằng 0. Điều đó phù hợp lbfgs gần như xác định trong setup này. Không được suy ra độ bất định bằng 0 trên các split hoặc domain khác; chỉ random_state được thay trong phép lặp này.

LinearSVC là so sánh bổ sung: validation chọn C=0,5 trong {0,5;1;2}; test macro-F1 0,667210 thấp hơn LR dù accuracy 0,818489 cao hơn. Đây là ví dụ chọn theo accuracy có thể đưa ra quyết định khác với macro-F1.
Nguồn: reports/task2/baseline_three_seed.csv; reports/task2/linearsvc_validation_selection.csv; scripts/task2_classical_comparison.py.
@@19|Qwen Proposed V1
V1 dùng Qwen2.5-1.5B-Instruct-GGUF Q4_K_M, chạy llama.cpp b11429. Model là bộ trọng số đã tiền huấn luyện; runtime là phần mềm thực thi trọng số. GGUF là định dạng; Q4_K_M là cấu hình quantization hỗn hợp trong họ K-quant, không phải mọi tensor đều chính xác bốn bit. Không có fine-tuning hoặc training LLM from scratch.

Ba prompt đóng băng: v1_a tối giản, v1_b định nghĩa nhãn, v1_c thêm ba ví dụ train-only không xung đột. Chọn bằng validation macro-F1, rồi JSON validity và latency. Qwen chỉ nhận text, phải trả JSON sentiment thuộc ba nhãn. Temperature=0, seed=42, output cap=32, tối đa hai attempts; parser/schema không âm thầm đổi free text thành label.

v1_c được chọn với validation macro-F1 0,641252. Test 887 mẫu cho macro-F1 0,621789, accuracy 0,732807 và JSON validity 1. JSON hợp lệ chỉ chứng minh định dạng, không chứng minh phân loại đúng. Tài nguyên đỉnh của evaluation V1 bị mất trong lỗi reporting; probe idle về sau không thay thế được peak inference.
Nguồn: qwen_v1.yaml; src/proposed_v1/runner.py; reports/proposed_v1/qwen_prompt_comparison.csv; reports/proposed_v1/qwen_resource_report.json.
@@20|Phân tích lỗi Proposed V1
V1 sai 237/887 mẫu; TF-IDF sai 169. Neutral V1 recall 0,674419 nhưng precision chỉ 0,159341: mô hình bắt được 29/43 gold-neutral nhưng dự đoán neutral quá nhiều. F1 0,257778 thấp hơn TF-IDF 0,413043. Không thể dùng recall đơn lẻ để tuyên bố neutral được cải thiện.

failure_counts cho sarcasm 9 lỗi trên 37 mẫu, mixed-marker 45/121, negation-marker 42/208, short text 33/93 và conflicting text 16/24. Các nhóm chồng lấp; chỉ sarcasm lấy nhãn nguồn, các marker khác là proxy lexical. Không cộng các tử số thành tổng lỗi và không coi proxy là annotation thủ công về hiện tượng ngôn ngữ.

DERIVED: macro-F1 V1 − rule = +0,190510; V1 − TF-IDF = −0,061065; neutral F1 V1 − TF-IDF = −0,155266. Có improvement so với rule, không có improvement so với baseline mạnh đã chọn. Thất bại này thúc đẩy thử prompt calibration và aspect input thay vì thay nhãn test.
Nguồn: reports/task2/failure_counts.csv; reports/proposed_v1/qwen_test_metrics.json; reports/baselines/tfidf_classification_report.csv.
@@21|V2 calibration và nghiên cứu aspect conditioned
V2-A vẫn text-only. Ba prompt v2_a1/a2/a3 dùng 6/9/8 ví dụ train, hiệu chỉnh cách hiểu neutral và các trường hợp sai ở validation V1. Chọn v2_a3 bằng validation macro-F1 0,632579. Test macro-F1 0,614487 và neutral F1 0,247104 đều thấp hơn V1 và TF-IDF. Vì test V1 đã được xem, kết quả V2 phải ghi exploratory reused test.

V2-B ở src/aspect_conditioned là protocol khác: text+aspect. Qwen text+aspect test macro-F1 0,602203; TF-IDF text+aspect 0,665514. Không được gọi V2-A là aspect-conditioned như một câu trong GAP_ANALYSIS/Q&A cũ. Hai protocol cần cột input riêng và không được dùng kết quả này làm benchmark text-only công bằng tuyệt đối.

Scientific lesson: prompt dài hơn, nhiều ví dụ hơn hoặc đầu vào giàu hơn không bảo đảm cải thiện. Tăng latency và token khi metric không tăng là bằng chứng chưa nên thay model demo. Một tập test ngoài chưa đụng tới vẫn cần cho xác nhận tiếp theo.
Nguồn: qwen_v2.yaml; qwen_aspect.yaml; reports/proposed_v2/prompt_comparison.csv; reports/aspect_conditioned/comparison.csv.
@@22|Aspect classification nhiều nhãn
Sentiment là multi-class: mỗi dòng một nhãn. Aspect là multi-label: một câu có thể cùng nói food, service và price. grouped_targets chuẩn hóa text rồi lấy hợp các aspect đã được annotation trong cùng split. Số đơn vị đánh giá đổi thành 3.768 train, 751 validation, 797 test; không chia lại membership.

Pipeline gồm TF-IDF unigram+bigram và OneVsRest Logistic Regression. Mỗi aspect có classifier nhị phân độc lập. Giá trị predict_proba ≥ threshold được chọn, cho phép không nhãn hoặc nhiều nhãn. C∈{0,5;2}, threshold∈{0,3;0,5;0,7}; chọn C=2, threshold=0,5 theo validation micro-F1, sau đó macro-F1 và C nhỏ hơn.

Aspect không được annotation bị coi là negative trong benchmark, dù annotation có thể thiếu. Không được mô tả target này như danh sách mọi aspect chắc chắn có trong câu. Model riêng giúp dashboard trả lời review đang nói về chuyện gì nhưng không tự đo sentiment của từng aspect.
Nguồn: src/foody/aspect.py; reports/aspect_classifier/selection.json; reports/aspect_classifier/validation_comparison.csv.
@@23|Metrics nhiều nhãn
Micro precision/recall cộng TP, FP, FN trên mọi cặp mẫu–aspect. Macro-F1 tính F1 từng aspect rồi trung bình, nên nhãn hiếm và zero support ảnh hưởng rõ. Exact match yêu cầu toàn bộ tập nhãn predicted giống gold của một mẫu.

EXAMPLE: gold={food,service}, predicted={food}; food đóng góp TP, service đóng góp FN, exact match của mẫu bằng 0. PROJECT RESULT: test micro-F1=0,832277; macro-F1=0,633628; exact match=0,726474; trung bình 1,063990 nhãn dự đoán/mẫu. Ba chỉ số đo những điều khác nhau nên không chọn một số rồi gọi chung là accuracy aspect.
Nguồn: src/foody/aspect.py::scores; reports/aspect_classifier/test_metrics.json.
@@24|Đọc kết quả từng aspect
Bảng per-aspect bên dưới cho thấy food, service, price có support lớn hơn các aspect hiếm. Food F1=0,877193 với 347 positives; service=0,814570 với 159; price=0,842105 với 139. Đây là số positive labels trên 797 grouped texts, không phải 887 sentiment rows.

amenities và room có test support=0, F1=0 do zero_division=0 và vẫn nằm trong macro tất cả chín nhãn. Không có evidence về năng lực phát hiện hai lớp này trên test; cũng không được tự bỏ chúng để cải thiện macro-F1 công bố. Chỉ có thể thêm một phép phân tích hỗ trợ với mẫu số nói rõ, giữ metric gốc.
Nguồn: reports/aspect_classifier/test_per_aspect.csv; src/foody/aspect.py.
@@25|Issue extraction là heuristic
extract_issues chỉ xét text khi overall predicted sentiment là negative và aspect tương ứng được dự đoán. Các cụm hẹp như “không ngon”, “phục vụ chậm”, “đợi lâu”, “giá cao”, “bất lịch sự” ánh xạ sang food_taste, slow_service, waiting_time, expensive, staff_attitude. Mỗi kết quả là tập unique issue names.

Code kiểm tra phủ định ngay trước cụm để tránh “không đắt” thành expensive. Nó không hiểu mọi sarcasm hoặc mixed sentiment; negative tổng thể có thể bỏ sót phàn nàn cục bộ trong review nhìn chung positive. Method được gắn heuristic_v1, không có supervised issue accuracy. Người bảo vệ nên gọi đây là tín hiệu hỗ trợ đọc review, không phải ground-truth complaint mining.
Nguồn: src/foody/enrichment.py::ISSUE_RULES, extract_issues; reports/foody_intelligence/issue_rules.json.
@@26|RAG từ đầu
LLM có thể sinh câu nghe hợp lý nhưng không có căn cứ trong dữ liệu nhà hàng. Retrieval-Augmented Generation đưa các review được tìm thấy vào prompt để câu trả lời có nguồn. Retrieval là tìm tài liệu; generation là viết lời đáp; validator kiểm tra output có bám nguồn không. Ba thành phần có failure mode khác nhau.

EXAMPLE: hỏi “Nhân viên phục vụ có vấn đề gì không?” tại Hanuri. Hệ thống cần review về service và đúng chiều phàn nàn; review chỉ khen giá rẻ không đủ trả lời. Không thấy bằng chứng phù hợp thì trả insufficient evidence. Có bằng chứng nhưng Qwen viết sai thì dùng extractive fallback. RAG không biến một vài review thành thống kê đại diện về toàn bộ khách hàng.
Nguồn: src/rag_v3/service.py; src/rag_v3/evidence.py; reports/task2/DOCKER_ACCEPTANCE.md.
@@27|Document chunk và token
Document là đơn vị nội dung có định danh và metadata; chunk là phần được cắt từ một document; token là đơn vị tokenizer mã hóa, có thể nhỏ hơn một từ tiếng Việt. Đếm ký tự hoặc từ không thay thế được token accounting. Cùng text, tokenizer MiniLM và Qwen có thể cho số token khác nhau.

Chunk size C giới hạn số token; overlap O lặp phần giáp ranh để giữ liên tục; stride S=C−O là bước dịch. Chunk nhỏ giảm nội dung thừa nhưng có thể cắt mất quan hệ phủ định hoặc ngữ cảnh. Chunk lớn giữ nhiều nghĩa hơn nhưng tăng chi phí và có nguy cơ bị truncation. Overlap tăng số token lưu/nhúng và đòi hỏi dedup khi tổng hợp evidence.
Nguồn: scripts/task2_rag_accounting.py; reports/task2/CHUNKING_DECISION.md.
@@28|Công thức số chunk
THEORY: với T>0, 0≤O<C, N=max(1, ceil((T−C)/(C−O))+1). Hàm max giữ ít nhất một chunk với văn bản ngắn; biểu thức ceiling đảm bảo phần đuôi không bị bỏ. Trong script, span_starts/policy_measure thực hiện chia chỉ bên trong từng review.

EXAMPLE — không phải số liệu project: T=900, C=256, O=32. S=224; (900−256)/224=2,875; ceil=3; N=4. Tổng vị trí token qua các chunk là T+(N−1)×O=996 nếu cửa sổ cuối được cắt đúng tại cuối text. Phải tính trên từng review rồi cộng, không nối 32.457 review thành một chuỗi lớn.
Nguồn: scripts/task2_rag_accounting.py; phụ lục công thức của tài liệu này.
@@29|Chính sách một review một document
prepare_rag lọc valid_for_ai có prediction và drop_duplicates(review_id), tạo JSONL với id, text, metadata. Index được chấp nhận chứa 32.457 document và vector tương ứng. Chính sách này giúp review_id–citation và filter restaurant nhất quán, không gộp review của nhà hàng khác.

Giới hạn quan trọng: MiniLM runtime được ghi nhận truncation 128 token. Có 11.235 review, tức 34,615029%, dài hơn 128 content tokens; phần đuôi có thể không ảnh hưởng embedding dù BM25 và evidence còn full text. Mean=115,550297, median=92, p95=288, max=2.124 token. 2.239 review vượt 256 và 222 vượt 512.

Không chọn 128/256/512 cho index mới trong task này vì chỉ có simulation workload, chưa có đánh giá retrieval của các index thay thế. Giữ index đã nghiệm thu là quyết định về tính nhất quán artifact, không chứng minh one-review là tối ưu về chất lượng.
Nguồn: src/foody/pipeline.py::prepare_rag; reports/task2/rag_token_statistics.json; reports/task2/chunking_comparison.csv.
@@30|So sánh chính sách chunk
Bảy policy được mô phỏng trên độ dài token thực, giữ ranh giới review và metadata. 128/0 tạo 46.968 chunks; 128/32 tạo 49.063; 256/0 tạo 34.962; 256/32 tạo 35.057; 512/0 tạo 32.688; 512/64 tạo 32.692. Overlap tăng workload nhưng không tạo thêm review gốc.

Thời gian thay thế được ước lượng bằng chunk_count / throughput đã đo. Không có embedding hoặc retrieval chạy lại trong các dòng simulation. Bảng dùng chữ DERIVED cho số chunk và estimated_seconds; thời gian index gốc là MEASURED. Khi đổi policy thật phải bổ sung chunk_id, aggregation về review_id và bộ relevance để đánh giá.
Nguồn: reports/task2/chunking_comparison.csv; reports/task2/embedding_workload.csv.
@@31|Token accounting
scripts/task2_rag_accounting.py nạp tokenizer JSON local, gọi no_padding và no_truncation để đếm content tokens không gồm special tokens. T_total là tổng độ dài; T_avg=T_total/N. Histogram cho phép tính lại median/percentile và số review vượt threshold mà không tokenize hay index lại.

PROJECT RESULT: MiniLM có 3.750.416 tokens, Qwen2.5 có 4.105.360 tokens trên cùng 32.457 review. Hai tổng thuộc hai vocabulary, không được cộng thành số billable duy nhất. Token của corpus cũng khác token request: request còn system instruction, question, chat template, selected evidence và retries.
Nguồn: reports/task2/rag_token_statistics.json; reports/task2/rag_token_distribution.csv; scripts/task2_rag_accounting.py.
@@32|Embedding và MiniLM
Embedding ánh xạ text sang vector số để so sánh gần nhau theo biểu diễn học được. EXAMPLE: “phục vụ chậm” và “đem món quá lâu” có thể gần nhau hơn hai câu không liên quan; đó là minh họa ý nghĩa semantic, không phải điểm similarity đã đo của project.

Model được chọn là sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2, dùng bản ONNX của Qdrant qua FastEmbed trên CPU. LocalEmbeddings chuẩn hóa vector L2 và kiểm tra dimension=384. 384 là kích thước kiến trúc model, không phải hyperparameter nhóm tune từ 128 lên 384. Repository không dùng SentenceTransformer trực tiếp cho runtime hiện hành dù tên model thuộc họ Sentence Transformers.

Dense similarity không bảo đảm cùng chiều sentiment hoặc đúng issue. Hai câu “dịch vụ rất tốt” và “dịch vụ rất tệ” có thể cùng chủ đề; vì vậy V3 thêm filter và compatibility rules.
Nguồn: src/rag/embeddings.py; reports/rag/embedding_selection.json; model card Sentence Transformers.
@@33|Tính bộ nhớ vector
DERIVED: 32.457 × 384 × 4 = 49.853.952 bytes = 49,853952 MB = 47,544434 MiB cho payload float32. MB chia 10⁶; MiB chia 2²⁰. Con số này không phải RAM tối đa hoặc dung lượng thư mục Chroma.

Chroma còn metadata, text, HNSW, SQLite và overhead; model ONNX và runtime cũng chiếm RAM riêng. Không cộng model disk size với raw vector estimate rồi gọi đó là VRAM. Appendix cung cấp phép tính chính xác bằng Python và nguồn N,d,dtype.
Nguồn: data/foody/vector_store/index_manifest.json; src/rag/embeddings.py::_embed.
@@34|Chọn embedding bằng evidence
Có một so sánh nhỏ thật, không phải không có benchmark. Pool 612 documents gồm 600 mẫu ngẫu nhiên và known-positive IDs, sáu câu hỏi. Potion multilingual 256 chiều có known-positive recall@10=0,166667, MRR=0,104167; MiniLM 384 chiều có 0,333333 và 0,333333. Quy tắc chọn recall@10 rồi MRR rồi query time chọn MiniLM.

Potion nhanh hơn nhiều trong đo pool nhưng chất lượng theo nhãn dương đã biết thấp hơn. Pool nhỏ và labels chưa đầy đủ; không có exhaustive embedding model benchmark. Chọn MiniLM trong hai ứng viên không chứng minh thắng mọi encoder hoặc tối ưu với full index. Full-index metric giảm so với pool là điều cần giải thích vì không gian cạnh tranh tăng.
Nguồn: src/rag/evaluation.py::compare_candidates; reports/rag/embedding_comparison.csv.
@@35|Chroma và metadata filtering
Chroma lưu collection persistent với cosine HNSW. id của vector bằng review_id; metadata gồm restaurant_key/name, timestamp, raw_rating, predicted_sentiment, aspects/issues dạng JSON và Boolean aspect_<name>. open_collection kiểm tra count bằng manifest trước khi dùng.

Filter giới hạn tập ứng viên đúng nhà hàng, khoảng ngày hoặc nhãn dự đoán. Chroma score là độ gần trong không gian embedding, không phải xác suất câu trả lời đúng. timestamp_epoch được code dùng cho thứ tự và filter từ timestamp local naive; không phải chứng cứ thời điểm UTC đã được xác nhận. Manifest cố định model hash và document hash để phát hiện mismatch.
Nguồn: src/rag/vector_store.py; src/rag/retriever.py; reports/task2/RAG_METADATA_SCHEMA.md.
@@36|BM25 và implementation SQLite
BM25 đánh giá mức phù hợp từ khóa bằng tần suất, độ hiếm của term và chuẩn hóa độ dài document. k1 điều khiển saturation của tần suất; b điều chỉnh tác động độ dài so với avgdl. Công thức tổng quát có trong phụ lục; áp dụng cụ thể còn phụ thuộc tokenizer và IDF của thư viện.

PROJECT CONFIG: src/rag_v2/lexical.py gọi bm25(reviews_fts) của SQLite FTS5, dùng unicode61 remove_diacritics 2. Code không tune k1/b; tài liệu SQLite ghi cố định k1=1,2 và b=0,75 cho hàm này. SQLite trả số âm để rank nhỏ hơn tốt hơn; code đảo dấu khi tạo ReviewHit.score. FTS query ghép unigram/bigram/trigram bằng OR, quote token và bind SQL parameters.

BM25 có thể bắt tốt cụm chê rõ ràng nhưng yếu với diễn đạt không chia sẻ từ. Bỏ dấu và stopwords ảnh hưởng matching; riêng từ “không” nằm trong stopwords unigram, trong khi phrase expression vẫn có thể chứa nó. Không mô tả BM25 như mô hình hiểu phủ định hoàn chỉnh.
Nguồn: src/rag_v2/lexical.py; SQLite FTS5 bm25 documentation.
@@37|Dense retrieval và lexical retrieval
Dense tìm theo vector semantic, BM25 tìm theo token/phrase. Dense hữu ích với paraphrase; BM25 có lợi khi câu hỏi và review chia sẻ cụm cụ thể. Cả hai có thể tìm sai polarity, nhà hàng hoặc thời điểm nếu thiếu filter.

V1 dense trong benchmark full index có known-positive recall@5 bằng 0; BM25 tìm thêm known positive. Đây là quan sát trên sáu câu, không phải bằng chứng dense luôn kém BM25. Cách kết hợp RRF tránh cộng trực tiếp cosine với BM25 vốn khác scale, nhưng vẫn cần kiểm tra evidence vì fusion chỉ đổi xếp hạng.
Nguồn: src/rag_v2/hybrid.py; reports/rag_v3/retrieval_policies.csv.
@@38|Reciprocal Rank Fusion
RRF(d)=Σ_r 1/(k+rank_r(d)); mỗi retriever góp một số theo thứ hạng, không dùng trực tiếp score của nó. rrf_fuse dùng k=60, rank bắt đầu từ 1, gộp theo review_id và tie-break theo ID. Candidate dense_top_n và lexical_top_n đều 20 trước lấy final top-k.

EXAMPLE: document A rank 1 và 4 có score 1/61+1/64≈0,032018; B rank 2 và 2 có 2/62≈0,032258. B nhỉnh hơn vì xuất hiện tốt ở cả hai. Đây là số minh họa, không phải retrieval score lưu của Hanuri.

Tăng k làm khác biệt giữa các thứ hạng đầu nhỏ hơn; giảm k ưu tiên top ranks mạnh hơn. k=60 và candidate pool 20 là engineering choices; chưa có sweep riêng chứng minh tối ưu.
Nguồn: src/rag_v2/hybrid.py::rrf_fuse, RetrievalConfig.
@@39|RAG V1 và giới hạn dense only
V1 dùng selected MiniLM và Chroma full index. Trong shared V3 policy run, recall trên known-positive tại 5=0, tại 10=0,083333, MRR=0,018519, mean retrieval=16,519117 ms. Các số này phải ghi đúng run; bảng V2 candidate có mean 15,761 ms là một lần đo khác.

Một lỗi chính là gần chủ đề nhưng sai bằng chứng: review khen phục vụ không trả lời được câu hỏi phàn nàn service. Thêm LLM vào phía sau không thể bảo đảm sửa retrieval thiếu bằng chứng. V1 là historical experiment, không phải path Analyst đang dùng.
Nguồn: reports/rag_v3/retrieval_policies.csv; src/rag/service.py; reports/task2/RAG_ABLATION_FINAL.md.
@@40|RAG V2 và hybrid candidates
V2 thử dense, BM25, RRF, RRF+expansion và evidence reranking. Expansion thêm các term theo intent đã giới hạn; auto_filter có thể thêm negative và aspect khi câu hỏi là complaint. Rerank cộng hoặc trừ các trọng số nhỏ dựa trên aspect, compatibility và issue matches, không phải neural cross-encoder.

Trong V2 candidate run, BM25 MRR=0,166667; RRF=0,041667; expansion và rerank=0,055556. Thêm complexity không tăng Hit/known-positive coverage ở tập nhỏ. Rerank cần khoảng 313,404 ms trong run đó; shared V3 run ghi 600,291 ms cho policy V2, không nên so như paired speedup.

V2 đã tìm được evidence food nhưng một câu trả lời bị loại do không đúng topic, rồi trả insufficient. V3 thêm extractive fallback để giữ được thông tin có căn cứ. Không thể tái dựng mọi lỗi JSON V2 vì raw rejected generations cũ chưa được lưu đầy đủ.
Nguồn: src/rag_v2/hybrid.py; src/rag_v2/service.py; reports/rag_v2/retrieval_candidates.csv.
@@41|RAG V3 và vai trò từng bước
route_query nhận dạng causal, complaint có aspect, general aspect hoặc summary. Complaint có aspect đi filtered BM25 kèm evidence rerank; general đi hybrid RRF. TREND_CAUSATION đi MART_TREND_GUARD và search_debug trả danh sách rỗng để không suy diễn nguyên nhân từ vài review. Tên guard không có nghĩa query handler luôn chạy một phép phân tích nhân quả trên mart.

build_packet giữ evidence hợp intent/polarity/topic, dedup text và lấy tối đa ba review. Qwen chỉ nhận packet này. attach_citation có thể gắn placeholder bằng overlap khi thiếu inline citation, nhưng sau đó vẫn phải qua validator. Tối đa hai lần sinh; không qua thì extractive_answer, không có evidence thì insufficient.

RRF không áp dụng mọi query; BM25 complaint route tắt dense. Evidence rules và clause validator là deterministic heuristic, chưa phải human entailment oracle. Code hiện tại và các ca nghiệm thu là phạm vi lời khẳng định “đã chấp nhận”.
Nguồn: src/rag_v3/routing.py; src/rag_v3/retriever.py; src/rag_v3/evidence.py; src/rag_v3/service.py.
@@42|Hit at k và sai lệch tên cột trong báo cáo cũ
THEORY: Hit@k(q)=1 nếu top-k có ít nhất một relevant document, ngược lại 0; mean Hit@k lấy trung bình trên query. EXAMPLE: ba query có hit [1,0,1] thì Hit@k=2/3. Đây là chỉ số có hoặc không có, không chia số hit cho số gold của từng query.

AUDIT: known_positive_scores trong src/rag/evaluation.py thực sự tính |top-k ∩ known positives|/|known positives|. scripts/evaluate_rag_v3_retrieval.py đổi tên trung bình này thành known_hit_at_5/10. Vì vậy giá trị 0,083333 đã công bố phải được mô tả là macro known-positive recall, không phải binary Hit@k. Tài liệu giữ nguyên số và nêu tên cột lịch sử để truy vết, không sửa experiment.
Nguồn: src/rag/evaluation.py::known_positive_scores; scripts/evaluate_rag_v3_retrieval.py; reports/rag_v3/retrieval_policy_rows.csv.
@@43|Mean Reciprocal Rank
MRR nhìn vị trí relevant đầu tiên: query có rank r góp 1/r, không tìm thấy góp 0. MRR là trung bình qua mọi query. EXAMPLE: ranks 1,4,missing cho (1+0,25+0)/3=0,416667. MRR không biết có bao nhiêu relevant khác phía sau.

PROJECT RESULT: V3 routed MRR known-positive=0,166667 trên sáu câu, tức tổng reciprocal ranks bằng 1. Điều này không có nghĩa 16,7% review corpus liên quan. Cần đọc query rows và tập known positives chưa đầy đủ để hiểu rank; reviewer chưa gán nhãn cho mọi tài liệu.
Nguồn: src/rag/evaluation.py; reports/rag_v3/retrieval_policy_rows.csv.
@@44|Recall at k và nhãn relevance chưa đầy đủ
Recall@k(q)=số relevant retrieved trong top-k / tổng số relevant của query. Full recall đòi hỏi biết đầy đủ tập relevant. Project chỉ có các known-positive IDs do người xây benchmark chọn, vì vậy các số recall trong tài liệu này đều ghi rõ known-positive, không phải full-corpus recall hoặc accuracy của search.

Một tài liệu không nằm trong known positives có thể vẫn thực sự liên quan. Vì thế low known-positive score không chứng minh mọi retrieved review đều sai, còn số cao cũng không chứng minh answer grounded. Context precision, context recall chuẩn hóa và đánh giá người dùng đầy đủ chưa có trong evidence này.
Nguồn: reports/rag/development_judgments.json; reports/rag/rag_metrics.json; src/rag/evaluation.py.
@@45|Evidence packet và citation
Packet chứa question_intent, aspect, restaurant, evidence và aggregates. Mỗi evidence có ref E1/E2/E3, review_id thật, sentiment/aspects/issues dự đoán, rating và đoạn text giới hạn. Payload generation dùng placeholder ngắn để giảm khả năng model viết sai một ID dài; response cuối map lại ID chính xác.

frequency_supported=False ngăn suy ra “đa số”, “thường xuyên” từ vài review đã chọn. accepted_review_count đếm evidence sau gate, không phải tổng review của nhà hàng. _packet_text thường lấy 350 ký tự hoặc đoạn quanh complaint cue; đây là truncation bằng ký tự ở packet, khác giới hạn token của embedding.
Nguồn: src/rag_v3/evidence.py::Packet, build_packet, _packet_text, evidence_for_refs.
@@46|Support validator và giới hạn heuristic
validate_packet_citations kiểm tra inline refs, danh sách refs, aspect/topic, polarity, số ít/số nhiều, frequency language và mixed evidence. Sau đó tách câu/mệnh đề, yêu cầu citation cho từng assertion và overlap với chính review được dẫn. _clause_supported còn kiểm tra các cue issue, polarity staff attitude và loại numeric claims được sinh.

Một câu có review ID đúng vẫn có thể chứa claim không có trong review. Do đó schema và citation validity chưa đủ. Tuy vậy overlap/cue rule cũng có thể bỏ sót hoặc loại nhầm paraphrase; số unsupported accepted bằng 0 là “validator không phát hiện” trong sáu ca, không phải chứng minh không hallucinate trên mọi đầu vào.
Nguồn: src/rag_v3/evidence.py::validate_packet_citations, _clause_supported; reports/rag_v3/generation_failure_analysis.json.
@@47|Fallback và từ chối khi thiếu bằng chứng
Khi có packet hợp lệ nhưng hai lần sinh không qua, extractive_answer chọn evidence đầu, trích tối đa khoảng 180 ký tự và gắn ref. Mode=extractive_fallback hiển thị cho người dùng. Đây là cơ chế bảo toàn evidence, nhưng answer có thể chưa đủ để trả lời câu hỏi “phổ biến nhất”.

Khi packet rỗng hoặc query causal bị guard, không gọi generation để cố tạo lời giải thích. Trả insufficient-evidence là hành vi đúng cho ba ca thiếu bằng chứng trong nghiệm thu. Fallback không phải crash, nhưng fallback nhiều vẫn cho thấy giới hạn generator; không dùng tỷ lệ answer hợp lệ sau fallback để quảng cáo khả năng synthesis thuần của LLM.
Nguồn: src/rag_v3/service.py::answer_question_v3; src/rag_v3/evidence.py::extractive_answer.
@@48|Qwen 1 phẩy 5B và 3B
B biểu thị tỷ tham số xấp xỉ, không phải dung lượng GB. Qwen 1,5B là model sentiment V1/V2 và cấu hình gateway mặc định lịch sử; accepted Streamlit V3 chọn Qwen 3B qua config/demo.yaml. Compose cũng mặc định file 3B, cho phép override rõ ràng bằng QWEN_MODEL_FILE.

Trong accepted replay sáu ca, cả hai model có 2 supported complete, 1 supported incomplete, 3 correct insufficient và 0 validator-detected unsupported accepted; fallback giảm từ 3 xuống 2 với 3B. Đây là tín hiệu demo nhỏ để chọn 3B, không phải general LLM ranking. Model file 3B=2.104,932768 MB và 1,5B=1.117,320736 MB; RAM/VRAM còn runtime và context overhead.
Nguồn: config/demo.yaml; qwen_v1.yaml; qwen_v3_3b.yaml; reports/rag_v3/generation_metrics.json; reports/task2/FEASIBILITY.csv.
@@49|Benchmark Qwen Llama DeepSeek
Ba model dùng cùng sáu saved evidence packets, prompt V3, llama.cpp b11429, temperature=0, seed=42, cap 128 output tokens, không rerun retrieval. Qwen2.5 3B và Llama-3.2 3B so với DeepSeek-R1-Distill-Qwen 1,5B. DeepSeek distill có gốc Qwen; gọi là ba nhãn họ sản phẩm không có nghĩa ba kiến trúc base độc lập cùng kích thước.

Final gate giữ cùng 2 complete, 1 incomplete, 3 insufficient ở cả ba; Qwen replay mới fallback 3, Llama 2, DeepSeek 3. DeepSeek không tạo schema parseable trong các ca answerable dưới protocol này; không kết luận model nói chung yếu. Qwen replay mới bị contention và chậm hơn accepted replay, nên không trộn hai lần đo.

Token response của lỗi timeout/parse thiếu phải để N/A. DeepSeek server-log counters 4.228 input và 768 output trên sáu attempts là nguồn đo khác, không điền vào cột successful-response usage. Ollama và llama.cpp là runtime, không phải model; benchmark thực tế này dùng llama.cpp.
Nguồn: reports/task2/llm_comparison.csv; reports/task2/llm_benchmark_provenance.json; reports/task2/LLM_BENCHMARK.md.
@@50|Latency mean p95 và phạm vi đo
Mean là tổng latency chia số quan sát; p95 là percentile 95, phản ánh phần đuôi chậm. Với numpy/pandas mặc định linear interpolation, p95 có thể nằm giữa hai mẫu. Chỉ sáu query thì percentile rất nhạy; không dùng nó như SLA ổn định cho người dùng thật.

Retrieval latency đo tìm ứng viên; generation latency đo các call hoàn thành; end-to-end gồm retrieval, gate, retries/fallback và overhead. Telemetry cộng usages chỉ của attempts có usage trả về, nên không luôn chứa thời gian timeout. Benchmark còn cột answerable wall time để phản ánh toàn bộ chờ ở các câu có evidence. Mean toàn sáu ca chứa ba refusal nhanh khác mean ba answerable.
Nguồn: src/rag_v3/service.py; scripts/task2_llm_benchmark.py; reports/task2/FEASIBILITY.csv.
@@51|Disk size RAM VRAM và quantization
Model_size_bytes là kích thước file weights trên đĩa; RSS là bộ nhớ resident của process; VRAM là bộ nhớ GPU. Sampling GPU toàn hệ thống có thể gồm ứng dụng khác và không chứng minh process inference dùng hết lượng đó. Context/KV cache, batch và runtime tạo overhead ngoài weights.

Q4_K_M giảm biểu diễn weights để model chạy trên máy cá nhân, có thể đổi quality. Repository không có đối chứng full precision để tính mất mát do quantization. V1 mất sampler evaluation, chỉ có idle probe riêng; three-family benchmark có sampled RSS nhưng GPU số đo system-wide. Docker nghiệm thu chạy CPU, GPU container NOT VERIFIED dù lệnh yêu cầu gpu layers=99.
Nguồn: reports/proposed_v1/qwen_resource_report.json; reports/task2/llm_comparison.csv; reports/task2/DOCKER_ACCEPTANCE.md.
@@52|MLOps và LLMOps
MLOps quản lý data/model version, training evaluation, reproducibility và phục vụ. MLflow lưu tham số, metrics, artifact của nghiên cứu; DVC mô tả phụ thuộc/stage. LLMOps còn cần model/prompt version, token, latency, schema, citations và cách đáp hoặc fallback. Project không đăng ký một production LLM mới.

record ghi SQLite state/llmops.sqlite với component, timestamp, model hash, prompt version, rag_version, retrieval_method, query_route, evidence_count, support_gate_status, clause_support_status, tokens và latency. safe_filters chỉ giữ restaurant_key, ngày, sentiment, aspect. Không lưu raw question/review trong operational event; intentional evaluation audit riêng có thể lưu raw generation nên không đồng nhất hai nơi.

Theo dõi mode và failure category giúp phát hiện model đang fallback nhiều dù HTTP vẫn 200. Health endpoint chỉ trả lời khả năng truy cập cơ bản, không thay thế quality monitoring.
Nguồn: src/rag/monitoring.py; src/ml/mlflow_tracking.py; src/rag_v3/service.py.
@@53|Bốn trang Streamlit
Restaurant Intelligence đọc marts, chọn nhà hàng/ngày, hiển thị rating, sentiment, aspect/issues và historical alerts; nút health report gọi V3 health service. Review Explorer đọc enriched reviews, lọc và phân biệt trường raw với predicted. AI Review Analyst nhận question/restaurant/filter, gọi RoutedRetriever và selected_v3_gateway trực tiếp trong process Streamlit, rồi hiển thị answer, evidence và mode.

LLMOps Monitor đọc events và report, tách số liệu nghiên cứu với inference demo. Dữ liệu đọc được cache bằng st.cache_data; cache không train lại model. Exception được hiển thị thành trạng thái RAG unavailable để frontend còn đọc dashboard. Đường Analyst hiện tại không gửi HTTP sang rag-backend; sơ đồ chuỗi Streamlit→FastAPI→Qwen sẽ mô tả sai source.
Nguồn: app/app.py::restaurant_page, explorer_page, analyst_page, monitor_page.
@@54|FastAPI và HTTP
API định nghĩa hợp đồng request/response qua HTTP. FastAPI ở app/api.py có GET /health, POST /ask và GET /restaurants/{restaurant}/health-report. Docker expose host port 8000; Streamlit là frontend ở 8501. HTTP 200 nghĩa endpoint xử lý được, không tự chứng minh một truy vấn RAG V3 đã chạy.

/ask hiện import src.rag.service.answer_question và LLMGateway mặc định lịch sử, không dùng answer_question_v3. /health kiểm tra index_manifest và file Qwen v1 1,5B, nên trường qwen_weights_available không phải xác minh model 3B đang serve. Accepted V3 query là đường Streamlit/CLI; tài liệu ghi rõ API là service bổ sung với path legacy, không sửa source trong task documentation.
Nguồn: app/api.py; docker-compose.yml; reports/task2/MICROSERVICE_ARCHITECTURE.md.
@@55|Docker từ đầu
Docker đóng gói chương trình và dependency thành image. Dockerfile là công thức build; container là một instance của image đang chạy hoặc đã kết thúc. Volume/bind mount đưa dữ liệu ngoài image vào container. Network cho service giao tiếp; port mapping đưa cổng container ra host; environment variable thay cấu hình tại runtime.

Compose gom khai báo service, build, command, ports, mounts và profile trong YAML. Dockerfile.rag dùng Python 3.12 và requirements-demo.txt cho Streamlit/FastAPI; Dockerfile lịch sử dùng Python 3.11 và requirements.txt cho pipeline CLI. Images không mang data/models private; chạy được demo cần mounts có artifact đúng hash.
Nguồn: Dockerfile; Dockerfile.rag; docker-compose.yml.
@@56|Image và container
Có thể hình dung image như bản mẫu đã đóng gói và container như một phiên thực thi từ bản mẫu đó. Cùng application image có thể chạy lệnh Streamlit hoặc uvicorn trong hai container khác nhau. Thay requirements trên host không tự sửa filesystem bên trong image đã build; phải rebuild rồi recreate service.

Container lưu writable layer riêng nhưng dữ liệu bind mount nằm trên host. Xóa container không đồng nghĩa xóa source artifact được mount; ngược lại ghi vào mount RW có thể thay file host. Vì vậy model/report mount dùng ro trong serving path; data/state vẫn có quyền ghi theo Compose hiện tại.
Nguồn: docker-compose.yml; Dockerfile.rag; reports/task2/DOCKER_ACCEPTANCE.md.
@@57|Các service Docker thực tế
Default services: pipeline chạy CLI help một lần; qwen chạy llama-server; rag-backend chạy FastAPI; streamlit chạy giao diện. prefect-server và scheduler nằm trong profile orchestration, không bật mặc định và không bắt buộc cho acceptance hiện tại.

Luồng đúng theo source: Browser → Streamlit :8501 → module RAG V3 trong container Streamlit → Qwen :8193; module đọc Chroma/BM25 qua data mount và ghi state SQLite. rag-backend :8000 là service song song có API legacy. Qwen local launcher dùng :8194; QWEN_BASE_URL=http://qwen:8193 trong Compose override URL kết nối.

Không gọi retrieval, validator hoặc monitoring là container độc lập: chúng là Python modules. Sơ đồ kiến trúc cần thể hiện ranh giới process để không phóng đại microservices.
Nguồn: app/app.py; app/api.py; src/llm/gateway.py; docker-compose.yml.
@@58|Mount dữ liệu model state và reports
Serving containers mount ./data→/app/data RW, ./models→/app/models RO, ./state→/app/state RW và ./reports→/app/reports RO. Qwen mount ./models→/models RO. Pipeline lịch sử chỉ mount data/state/logs. Các đường container khác host Windows nhưng giữ relative project structure.

Không bake weights, review private và indexes vào image giúp giảm artifact build, tránh đưa data riêng lên GHCR và cho phép phục hồi đúng phiên bản ngoài image. Đổi file mount vẫn có thể gây hash mismatch; pin manifest và preflight cần thiết. RO là thuộc tính mount, không phải mã hóa hay cơ chế bảo vệ toàn host.
Nguồn: docker-compose.yml; .dockerignore; .gitignore; src/demo.py.
@@59|Case study lỗi đường dẫn Windows và Linux
embedding_selection.json lưu model_file dạng models\embeddings\...\model_optimized.onnx. Linux Path không coi backslash là separator như Windows nên lookup nhắm vào một tên file chứa dấu backslash và gây FileNotFoundError dù file thật đã được mount.

selected_retriever thay separator khi đọc saved path rồi vẫn kiểm checksum model. Fix này không rebuild embedding hoặc đổi model. Bài học là artifact metadata có thể mang giả định hệ điều hành; mount đúng chưa đủ nếu serialized path sai. Báo cáo Docker giữ traceback và xác minh file readable để phân biệt nguyên nhân path với mất dữ liệu.
Nguồn: src/rag/cli.py::selected_retriever; reports/task2/DOCKER_ACCEPTANCE.md.
@@60|Case study thiếu psutil trong pipeline
Traceback của pipeline là ModuleNotFoundError: No module named 'psutil'. src.cli import rag_v3.cli → llm.gateway → proposed_v1.runtime, nơi import psutil. Image pipeline cài requirements.txt, trong khi psutil đã có ở requirements-demo.txt; sửa file demo sẽ không sửa dependency của pipeline.

Fix đã chấp nhận thêm psutil==7.2.2 vào requirements.txt rồi docker compose build pipeline và up -d pipeline. Import probe tải được psutil và src.cli; lệnh --help hoàn tất exit 0. Không chạy ingestion để kiểm tra một lỗi xảy ra ngay lúc import. Task tài liệu này chỉ mô tả fix đã có.
Nguồn: requirements.txt; Dockerfile; src/proposed_v1/runtime.py; reports/task2/DOCKER_ACCEPTANCE.md.
@@61|Đọc trạng thái Exited 0
Pipeline default command là python -m src.cli --help. Nó là one-shot: in usage rồi kết thúc. Exited (0) xác nhận hành vi này thành công; không cần giữ process bằng sleep để gọi healthy. Exit non-zero trước action mới là startup failure cần điều tra.

docker compose ps thường chỉ hiện service chạy; dùng ps -a để thấy one-shot đã hoàn tất. Qwen có Docker healthcheck thật; backend và Streamlit trong Compose hiện chưa có Docker healthcheck, nhưng HTTP health đã trả 200. Viết “Up và HTTP 200” chính xác hơn gán nhầm trạng thái Docker healthy cho cả ba.
Nguồn: Dockerfile; docker-compose.yml; reports/task2/DOCKER_ACCEPTANCE.md.
@@62|YAML trong project
YAML biểu diễn key:value, list bằng dấu gạch đầu dòng hoặc ngoặc vuông, và nesting bằng indentation. .yml và .yaml chỉ là hai đuôi của cùng định dạng. Trong Compose, services là mapping; streamlit là key; build/context/dockerfile là các cấp con; ports và volumes là list. Không thay indentation bằng tab.

Các chuỗi ${QWEN_MODEL_FILE:-...} trong Compose là interpolation runtime; ${{ github.ref }} trong GitHub Actions là expression của workflow engine. Chúng không phải Python syntax. Một parser YAML generic có thể xử lý từ on khác kỳ vọng YAML 1.2; đọc workflow phải theo semantics của GitHub Actions, không suy kết quả chỉ từ một thư viện parse.
Nguồn: docker-compose.yml; .github/workflows/ci.yml; .github/workflows/release.yml.
@@63|Git và lịch sử source
Repository lưu lịch sử snapshot theo commit. Branch main trỏ vào commit; remote origin là URL repository; fetch lấy remote refs; pull lấy và tích hợp; push gửi commit; tag đánh dấu một phiên bản. Rebase đặt lại các commit local lên base mới và đổi commit IDs, nên cần hiểu lịch sử trước khi dùng.

EXAMPLE minh họa: nếu README được sửa trên GitHub trong khi local có commit riêng, push có thể bị non-fast-forward. git fetch origin rồi xem log/diff, git pull --rebase origin main, giải quyết conflict, chạy kiểm tra và push lại có thể tích hợp an toàn. Không có log trong repo đủ chứng minh chuỗi push rejection cụ thể đã xảy ra; tài liệu không trình bày ví dụ này như sự kiện đã xác minh. Không cần force push để giải quyết trường hợp minh họa đó.

PROJECT VERIFIED: HEAD 4229a8b3998392c97f4b7a8c9e3795830285dbce, tag v1.0.1, cùng commit CI/release đã kiểm tra. Tài liệu mới tạo sau commit này nên chưa được bao phủ bởi run đó.
Nguồn: git log/tag tại audit; reports/task2/CICD_EVIDENCE.md; public GitHub Actions API.
@@64|Continuous Integration và Delivery
CI tự động kiểm tra source mới để phát hiện lỗi trước khi tích hợp. CD ở project là build và publish application image lên GitHub Container Registry. Workflow không khai báo remote deployment environment, database migration hay rollout production; publish thành công không có nghĩa người dùng ngoài Internet đã truy cập ứng dụng.

Runtime acceptance local bổ sung phần CI artifact-free không kiểm: weights, Foody index, Qwen health, real query và LLMOps event. Hai nhóm evidence trả lời hai câu hỏi khác nhau: source/image có build được, và artifact-mounted demo có thực thi được.
Nguồn: .github/workflows/ci.yml; .github/workflows/release.yml; reports/task2/DOCKER_ACCEPTANCE.md.
@@65|GitHub Actions từ workflow đến step
Workflow là file YAML mô tả tự động hóa. Trigger quyết định khi chạy; job chạy trên runner; step có thể là action uses hoặc lệnh run. checkout lấy source, setup-python chọn interpreter, cache pip giảm tải cài đặt. Secret/token cấp quyền cần thiết mà không hardcode vào source.

CI cấp contents:read; release thêm packages:write để publish GHCR bằng GITHUB_TOKEN. concurrency CI hủy run cùng ref cũ khi có run mới, còn release cancel-in-progress:false để tránh bỏ dở publication. Token không được đưa vào tài liệu hoặc log; chỉ mô tả tên biến và vai trò.
Nguồn: .github/workflows/ci.yml; .github/workflows/release.yml.
@@66|Giải thích ci yml thực tế
CI chạy khi push main/develop, pull request tới main và workflow_dispatch. Job quality-and-tests dùng ubuntu-latest, Python 3.12, requirements-ci.txt, Ruff, compileall src app scripts, pytest xuất JUnit, rồi import app.app và app.api. Upload JUnit dùng if:always để có report cả khi test lỗi.

Job docker-build validate Compose và build Dockerfile.rag với tag food-review-intelligence:ci. CI không download weights, train hoặc rebuild Foody index. Synthetic tests và import không chứng minh model riêng sẵn sàng; demo-preflight thực cần local artifacts. requirements-ci khác runtime dependencies là phân chia mục tiêu môi trường, không phải thiếu bằng chứng build pipeline.
Nguồn: .github/workflows/ci.yml; requirements-ci.txt.
@@67|Giải thích release yml thực tế
Release trigger v* tag hoặc workflow_dispatch với version. Step validate kiểm regex vMAJOR.MINOR.PATCH có thể có prerelease; setup-buildx tạo builder; login-action đăng nhập ghcr.io bằng github.actor/GITHUB_TOKEN; metadata-action sinh tags; build-push-action build Dockerfile.rag và push:true.

Tag push stable tạo ref tag, version không v, major.minor và latest theo cấu hình; prerelease không tạo latest qua điều kiện explicit. Manual dispatch có raw input version và semantics khác tag push; không giả định mọi alias luôn xuất hiện. Git tag v1.0.1 có sẵn nên không tạo lại trong hướng dẫn reproducibility.
Nguồn: .github/workflows/release.yml.
@@68|GHCR và release đã xác minh
GHCR là registry lưu image layers và manifests; URL ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 chỉ một image reference. Tag thuận tiện nhưng có thể thay đổi; digest xác định nội dung manifest. Release hiện xác minh index digest sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a, có linux/amd64 manifest.

CI run 39739640437 và release run 39742439011 đều success tại commit 4229a8b3998392c97f4b7a8c9e3795830285dbce. Đây là cập nhật mới hơn CICD_EVIDENCE.md còn nhắc v1.0.0. Tài liệu lưu kiểm tra read-only ngày 22/10/2026; không sửa workflow hoặc phát hành image mới.
Nguồn: public GitHub Actions run URLs trong Evidence Map; docker buildx imagetools inspect v1.0.1 tại audit.
@@69|Semantic version
Semantic version có ba thành phần MAJOR.MINOR.PATCH. Về nguyên tắc, major báo thay đổi không tương thích, minor thêm chức năng tương thích, patch sửa lỗi tương thích. Trong project, v1.0.1 là tag sau fix runtime Docker; không suy diễn version package pyproject.toml=0.1.0 phải trùng release image tag.

Workflow chỉ kiểm cấu trúc version, không tự chứng minh mức thay đổi đúng quy ước semantic. Khi chuẩn bị release tương lai cần chọn tag chưa tồn tại, chờ CI của đúng commit và xem manifest. Tài liệu mô tả quy trình; không thực hiện commit/push/tag.
Nguồn: .github/workflows/release.yml; pyproject.toml; git tag --list.
@@70|Bản đồ repository
Source map dưới đây nối file với vai trò, input/output và caller. Nhánh src/food, src/baselines, src/proposed_v1/v2 và src/aspect_conditioned là nghiên cứu; src/foody xử lý dữ liệu/inference offline; src/rag và src/rag_v2 có thành phần được V3 tái sử dụng; src/rag_v3 cùng app là đường phục vụ hiện hành.

databricks, crawler, orchestration và một phần src/ml giữ lịch sử hoặc utility còn được tests/audits tham chiếu. Không xóa chúng khi đọc kiến trúc, cũng không đặt chúng vào luồng demo nếu không có caller hiện hành. scripts chứa cả thao tác làm thay đổi artifact và verify; tên script không đủ biết read-only, phải đọc function body.
Nguồn: inventory AST toàn src/app/scripts/tests; README.md; src/cli.py.
@@71|Walkthrough function và class chính
Đọc chương trình theo dòng dữ liệu hiệu quả hơn đọc tên file tuần tự. Bắt đầu từ app.app.analyst_page hoặc src.cli.main, theo command dispatch tới prepare_question, route_query, search_debug, build_packet, gateway.generate, validation/fallback và record. Với offline research, theo load_splits → build_pipeline → fit train → validation selection → test checkpoint → metrics/artifact.

Walkthrough phía dưới trình bày input, output, logic, caller/callee và failure ở các function thật. Signature và line numbers được lấy bằng AST trong audit; pseudo-code là diễn giải, không phải đoạn source có thể dùng thay production. Các thao tác train/index được mô tả để hiểu và không được chạy lại trong task này.
Nguồn: source hiện tại; scripts/documentation/audit_repository.py.
@@72|Model được build ra sao
Sentiment: import source pinned → filter vi/restaurant → NFC/whitespace → sign labels → connected-component split → fit TF-IDF và LR trên train → chọn n-gram/C bằng validation → freeze → test một lần trong protocol baseline → lưu models/tfidf_logreg.joblib → Foody predict_proba. Rating/aspect không đi vào text-only sentiment features.

Aspect: dùng frozen split → group normalized text trong split → union aspect targets → MultiLabelBinarizer theo train classes → TF-IDF + OVR LR → validation C/threshold → checkpoint test → lưu models/aspect_tfidf.joblib. Enrichment chỉ load artifacts, không gọi train.

LLM: lấy weights pretrained đã pin revision/hash → load bằng llama.cpp → prompt inference/evaluation. Không có pipeline pretrain Qwen/Llama/DeepSeek từ raw Foody. Các experiment prompt không cập nhật weights.
Nguồn: src/baselines/runner.py; src/foody/aspect.py; src/foody/enrichment.py; reports/task2/TRAINING_SCOPE.md.
@@73|Fit và transform
fit học vocabulary và IDF từ train; transform dùng đúng vocabulary/IDF đó để mã hóa dữ liệu mới. Trong sklearn Pipeline, fit(train_texts, labels) fit transformer rồi classifier; predict/transform validation/test chỉ áp dụng thành phần đã học. Token chưa có vocabulary không tự tạo chiều mới lúc predict.

Nếu fit TF-IDF trên toàn dataset trước khi split, IDF và vocabulary đã dùng thông tin test dù chưa dùng label. Đó là leakage preprocessing. Code hiện tại đóng gói transformer vào pipeline được fit train-only; đọc source và frozen protocol quan trọng hơn chỉ thấy câu “we split data” trong report.
Nguồn: src/baselines/tfidf_logreg.py; src/baselines/runner.py; tests/test_food_baselines.py.
@@74|Offline research flow
Dataset revision và raw hashes xác định nguồn; preparation hash xác định dữ liệu chuẩn hóa; split hash xác định membership. Runner chọn cấu hình từ validation, lưu model/prompt/protocol hashes, predictions và metrics. MLflow run_id cho phép nối candidate với evidence. DVC khai báo quan hệ dependencies và outputs, không đảm bảo một lệnh reproduce sẽ nhẹ.

Historical experiments đã hoàn tất nên không chạy dvc repro toàn bộ chỉ để xem demo. Có checkpoint/guard tránh vô tình đánh giá test lần hai, nhưng nghiên cứu V2 vẫn công khai test đã được nhìn. Reproducibility nghĩa có thể truy vết và thiết lập lại điều kiện, không có nghĩa mọi hệ điều hành sẽ tạo timing hoặc bit-identical floating point giống nhau.
Nguồn: dvc.yaml; dvc.lock; params.yaml; src/baselines/runner.py; src/proposed_v1/runner.py.
@@75|Offline Foody flow
foody_reviews.csv → immutable snapshot → processed giữ source_row/original text → grouped observations → sentiment/aspect inference → issue rules → enriched join lại mọi dòng → distinct-review marts → documents.jsonl → embedding/Chroma và FTS5/BM25. Mỗi chuyển đổi có hash/manifest hoặc report để theo lineage.

Không xem dedup observation là xóa dữ liệu: original records vẫn ở processed/enriched, predictions được join many-to-one. Không suy ra predicted_negative_rate là tỷ lệ khách thực sự không hài lòng trong dân số, do sample crawl, classifier error và domain shift. RAG lấy những review đã có evidence, không tạo gold labels mới.
Nguồn: src/foody/cleaning.py; src/foody/enrichment.py; src/foody/analytics.py; src/foody/pipeline.py.
@@76|Online query flow
Browser gửi tương tác tới Streamlit. analyst_page tạo RetrievalRequest từ text/filter và chọn gateway 3B. RoutedRetriever kiểm manifest rồi chọn policy; packet gate lọc evidence; gateway gửi chat JSON qua HTTP llama.cpp; validator kiểm từng clause; response cuối mang mode/citations; record ghi telemetry.

Nghiệm thu Hanuri với câu “Nhân viên phục vụ có vấn đề gì không?” trả extractive_fallback có citation thật và event LLMOps. Log đã lưu event 403 với retrieval khoảng 5.027 ms, LLM khoảng 41.969 ms, end-to-end khoảng 47.415 ms trên container CPU. Đây là một request runtime khác accepted GPU/local replay, không dùng để thay các metric benchmark đã đóng băng.
Nguồn: app/app.py::analyst_page; reports/task2/DOCKER_ACCEPTANCE.md.
@@77|Testing và acceptance
Unit tests kiểm hàm nhỏ như normalization, label mapping, JSON/citation validation. Synthetic integration nối vài thành phần bằng fixture/fake runtime. Smoke kiểm import hoặc endpoint cơ bản. Acceptance dùng artifact thật để xác nhận đường demo và một câu hỏi thực; không đồng nghĩa đánh giá tổng quát chất lượng.

Kết quả gần nhất được ghi trong bằng chứng và phiên nghiệm thu là 288 passed, 1 warning, Ruff PASS, compileall PASS. Đây là kết quả kiểm tra trước task tài liệu, không phải suite chạy mới lúc viết Word. Test count 287 trong KEY_NUMBERS.json là snapshot cũ. Các test_rag_v3, test_demo_preflight, test_food_baselines, test_foody_intelligence giúp truy vết những hợp đồng chính.
Nguồn: tests/; reports/task2/REVIEW2_STATUS_SUMMARY_VI.md; reports/final/KEY_NUMBERS.json.
@@78|Bảo mật và an toàn câu trả lời
Grounding và fallback giảm việc đưa claim không có evidence; filter ngăn lấy nhầm nhà hàng/ngày; schema cấm field lạ; citations map về review IDs thực. Những guard này là kiểm soát chất lượng trong demo, không phải chứng nhận chống mọi prompt injection hoặc mọi hallucination.

Weights, Foody data, vector stores, .env và SQLite runtime được ignore; CI sử dụng fixtures; model/report mounts RO. Operational logs không lưu raw content. Tuy nhiên data/state mounts RW, input review vẫn là dữ liệu không tin cậy, và evaluation files riêng có thể chứa text. Phải phân biệt kiểm soát đã thực hiện với kiểm toán security chưa có.
Nguồn: .gitignore; .dockerignore; src/rag/monitoring.py; src/rag_v3/evidence.py; docker-compose.yml.
@@79|Kiến trúc cuối cùng
Hình tổng thể tách research offline khỏi demo. Classifier cổ điển tạo nhãn dự đoán; retrieval tìm bằng chứng; LLM diễn đạt; validator/fallback quyết định đầu ra được chấp nhận. Vì thế “LLM everything” không phù hợp evidence hiện tại: TF-IDF phân loại tốt hơn V1 và nhỏ/nhanh hơn trong các đo đã có, còn LLM có khả năng viết câu.

Hình kiến trúc logic không mô tả mọi network hop. Deployment thực có Streamlit gọi modules trực tiếp và kết nối Qwen; backend là service phụ legacy. Các khối MLflow/SQLite/Chroma là storage hoặc thư viện, không phải tất cả đều là container độc lập. Không đưa Databricks vào kiến trúc phục vụ cuối chỉ vì source lịch sử còn trong repository.
Nguồn: reports/task2/figures/final_architecture.png; app/app.py; docker-compose.yml.
@@80|Điều thành công thất bại và bài học
Rule thành công như baseline dễ giải thích nhưng nhiều neutral false positives. TF-IDF nâng macro-F1 và trở thành classifier demo; neutral vẫn yếu. Qwen V1 vượt rule nhưng thua TF-IDF. V2-A calibration và V2-B aspect input chưa mang cải thiện xác nhận; bài học là chọn theo evidence thay vì độ phức tạp.

RAG V1 chưa tìm tốt known positives; V2 hybrid cải thiện một số truy xuất nhưng sinh câu còn lỗi; V3 giữ useful evidence bằng fallback và guard. Docker từng gặp serialized path Windows/Linux và dependency psutil; sửa đúng nguồn dependency/path giúp nghiệm thu mà không retrain. CI/CD đã build/test/publish image, còn remote deployment không nằm trong phạm vi.
Nguồn: reports/task2/GAP_ANALYSIS.md; reports/task2/RAG_ABLATION_FINAL.md; reports/task2/DOCKER_ACCEPTANCE.md.
@@81|Giới hạn và bước nghiên cứu tiếp theo
Giới hạn dữ liệu: label aspect-level có xung đột text-only; neutral ít; Foody không có gold labels; tên nhà hàng chưa là ID chính thức; sampling review có thiên lệch. Giới hạn model: probability chưa calibrated Foody, issue heuristic, zero-support aspects và một số lựa chọn parameter chưa có controlled search.

Giới hạn RAG: sáu query với relevance chưa đầy đủ, truncation embedding dài, rule support không phải human entailment, latency khác run/hardware và generator fallback nhiều. Ablation là observed progression, không có packet-off/validator-off/fallback-off controls. GPU Docker chưa được xác minh; không train LLM from scratch; CD không phải remote production deployment.

Ưu tiên nghiên cứu tiếp theo là thêm relevance/human support labels độc lập, đánh giá chunked index riêng cho review dài và đo robustness trên domain mới. Đây là khuyến nghị dựa trên failure evidence, không triển khai feature mới hoặc tự nhận V4 đã tồn tại.
Nguồn: reports/task2/TRAINING_SCOPE.md; reports/task2/LLM_BENCHMARK.md; reports/task2/CHUNKING_DECISION.md.
@@82|Bảng lựa chọn tham số
Bảng và các thẻ phía dưới phân biệt hai loại bằng chứng. Validation-selected nghĩa có các ứng viên và điểm validation được lưu; engineering choice nghĩa giá trị đang dùng nhưng chưa có controlled experiment độc lập để chứng minh tối ưu. Một parameter có thể là architecture-fixed, như embedding dimension, thay vì knob tự do.

Hãy bảo vệ quyết định bằng thứ tự: định nghĩa → ảnh hưởng → ứng viên thật → metric chọn → kết quả → giới hạn → điều dự kiến khi tăng/giảm. Các dự kiến tăng/giảm là lý thuyết có điều kiện, không phải số đo đã chạy. Không dùng từ optimal cho grid ba trial hoặc smoke sáu ca.
Nguồn: src/baselines/tfidf_logreg.py; src/foody/aspect.py; src/rag_v2/hybrid.py; configs và CSV candidate.
@@83|Phiếu bảo vệ quyết định kỹ thuật
Các thẻ quyết định dưới đây dùng để trả lời “tại sao giá trị này”. Mỗi thẻ chỉ ra lựa chọn đang dùng, alternatives đã có hoặc chưa thử, evidence và uncertainty. Có thể mở thẳng file nguồn ghi ở cuối thẻ khi giảng viên hỏi. Cụm “chưa có controlled experiment” là giới hạn khoa học, không phải bỏ qua giải thích kỹ thuật.
Nguồn: parameter registry và Evidence Map trong tài liệu này.
@@84|Câu hỏi bảo vệ và trả lời
Phần Q&A dùng hai tầng: câu ngắn để trả lời trực tiếp và giải thích sâu để nối về code, công thức, evidence. Không học thuộc số lẻ mà quên đơn vị đếm hoặc phạm vi. Với metric chưa đo, câu trả lời đúng là nêu thiếu evidence và cách kiểm chứng cần làm, không điền một giá trị ước đoán.
Nguồn: source audit; reports/task2/; các bảng kiểm chứng trong tài liệu này.
@@85|Cheat sheet trình bày và vận hành
Năm trang tra cứu cuối chương gom số liệu, model, luồng chạy, lệnh và giới hạn. Sử dụng như bảng nhắc khi demo; các chương trước và notebook tính toán là nơi giải thích chi tiết. Những lệnh train/index chỉ xuất hiện như mô tả nghiên cứu, không phải yêu cầu chạy lại demo.
Nguồn: README.md; config/demo.yaml; reports/task2/; scripts/start_demo.ps1.
"""

REPORT_TITLES = [
    "Bài toán và phạm vi",
    "Nguồn dữ liệu",
    "Làm sạch và gán nhãn",
    "Train validation test và leakage",
    "Mất cân bằng lớp",
    "Chuẩn bị dữ liệu RAG",
    "Baselines",
    "Độ ổn định ba seed",
    "Paper và kết quả nhóm",
    "Gap analysis",
    "Proposed V1",
    "Failure analysis",
    "Proposed V2",
    "RAG V1 V2 V3",
    "Quyết định chunking",
    "Embedding và vector database",
    "Đánh giá retrieval",
    "Generation và faithfulness",
    "Ablation theo bằng chứng",
    "Benchmark ba LLM",
    "Tính khả thi",
    "Kiến trúc hệ thống",
    "Docker và microservices",
    "CI CD",
    "Reproducibility",
    "Luồng demo cuối",
    "Giới hạn",
    "Kết luận",
    "Checklist Task 2",
    "Phụ lục",
]
