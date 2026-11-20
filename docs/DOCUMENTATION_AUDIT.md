# Documentation audit

Audit read-only 22/10/2026; source HEAD4229a8b. Đã đọc 515 file text/source, phân tích AST của Python và checksum701 file protected trước authoring. Inventory là phân tích static; caller động có thể không suy ra hết. Các file dataset/model binary được checksum/đối chiếu manifest, không coi là văn bản để đọc. Không có claim đã kiểm toán mọi byte dependency bên thứ ba.

Bảng 1. Claim and metric audit

| Claim / Metric | Documented value | Type | Source | Recalculated? | Verified? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Research source rows | 76785 | MEASURED | reports/food_dataset_report.json | Có đối chiếu metadata | Có | Toàn nguồn đa ngôn ngữ |
| Vietnamese restaurant rows | 5869 | MEASURED | reports/food_dataset_report.json | Có | Có | Đơn vị sentence/aspect |
| Review IDs | 1530 | MEASURED | reports/food_dataset_report.json | Metadata đối chiếu | Có | Không bằng rows |
| Normalized texts | 5316 | MEASURED | reports/food_dataset_report.json | 3768+751+797 | Có | Aspect group count |
| Sentiment distribution | {"positive": 3714, "negative": 1861, "neutral": 294} | MEASURED | reports/task2/class_distribution.csv | Tổng 5869 | Có | Class counts không đổi bởi weighting |
| Imbalance ratio | 12.632653 | DERIVED | reports/task2/class_distribution.csv | Có | Có | majority/minority |
| Split rows | {"train": 4140, "test": 887, "validation": 842} | MEASURED | data/food/splits/metadata.json | Tổng 5869 | Có | Seed42 |
| Leakage checks | {"review_ids_spanning_splits": 0, "normalized_texts_spanning_splits": 0} | MEASURED | data/food/splits/metadata.json | Không resplit | Có | Không đảm bảo near duplicates |
| Split SHA256 | 860387be19c64220f91cc2b5e764aa3c99aa18daba9c776fde38e05da30a5ff9 | MEASURED | data/food/splits/metadata.json | Checksum audit | Có | Giữ frozen input |
| Foody raw rows | 33946 | MEASURED | reports/foody_intelligence/cleaning.json | 33938+8 | Có | Mọi source row được giữ |
| Foody valid rows | 33938 | MEASURED | reports/foody_intelligence/cleaning.json | 33946−8 | Có | Không phải 31694 |
| Foody inference observations | 31694 | MEASURED | reports/foody_intelligence/cleaning.json | Không rerun inference | Có | Restaurant key + normalized text |
| Foody distinct valid reviews | 32457 | MEASURED | reports/foody_intelligence/cleaning.json | Đối chiếu manifest | Có | RAG documents |
| Foody restaurants | 2110 | MEASURED | reports/foody_intelligence/cleaning.json | Không fuzzy merge | Có | Name-derived identity |
| Rule test macro-F1 | 0.431279 | MEASURED | reports/baselines/rule_based_test_metrics.json | Confusion recalculated | Có | Frozen text-only |
| TF-IDF test macro-F1 | 0.682854 | MEASURED | reports/baselines/tfidf_test_metrics.json | Confusion recalculated | Có | Frozen text-only |
| Qwen V1 test macro-F1 | 0.621789 | MEASURED | reports/proposed_v1/qwen_test_metrics.json | Saved result | Có | Frozen text-only |
| Qwen V2-A test macro-F1 | 0.614487 | MEASURED | reports/proposed_v2/test_metrics.json | Saved result | Có | Exploratory |
| Three-seed test macro-F1 | 0.682854 ± 0 (sample SD) | DERIVED | reports/task2/baseline_three_seed.csv | Có | Có | Cùng membership |
| Aspect micro/macro F1 | 0.832276657 / 0.633628001 | MEASURED | reports/aspect_classifier/test_metrics.json | Per-class đối chiếu | Có | 797 groups; room/amenities support0 |
| RAG documents/vectors/BM25 | 32457 / 32457 / 32457 | MEASURED | reports/task2/DOCKER_ACCEPTANCE.md | Manifests audit | Có | Không rebuild |
| MiniLM corpus tokens | 3750416 | MEASURED | reports/task2/rag_token_statistics.json | Histogram sum | Có | No special tokens; no truncation khi đếm |
| Qwen corpus tokens | 4105360 | MEASURED | reports/task2/rag_token_statistics.json | Histogram sum | Có | Vocabulary khác MiniLM |
| Embedding dimensions | 384 | CONFIGURED/EXTERNAL | src/rag/embeddings.py | Shape check code | Có | Architecture-fixed |
| Embedding seconds | 1054.633673 | MEASURED | data/foody/vector_store/index_manifest.json | Không re-embed | Có | Embedding compute sum |
| Raw vector bytes | 49853952 | DERIVED | src/rag/embeddings.py; Chroma manifest | Có | Có | Không phải Chroma disk |
| Dense/V2/V3 MRR | 0.018518519 / 0.055555556 / 0.166666667 | MEASURED | reports/rag_v3/retrieval_policies.csv | Giữ score gốc | Có | Incomplete positives, sáu query |
| Historical Hit@5/10 naming | Actual formula = macro known-positive recall | SOURCE AUDIT | src/rag/evaluation.py | Formula traced | Có | Không đổi experiment file |
| V3 accepted generator | 2 complete / 1 incomplete / 0 unsupported / 3 insufficient / 2 fallback | MEASURED | reports/rag_v3/generation_metrics.json | Saved counts | Có | Validator-detected only |
| Three-family benchmark | 6 cases per model | MEASURED | reports/task2/llm_comparison.csv | Saved rows | Có | Không general ranking |
| Latency and model sizes | Tách từng task/run; xem bảng feasibility | MEASURED | reports/task2/FEASIBILITY.csv | Không đo mới | Có | N/A giữ nguyên; DeepSeek wall-time fallback |
| Docker | pipeline exit0; qwen healthy; backend/UI HTTP200 | MEASURED | reports/task2/DOCKER_ACCEPTANCE.md | Reuse acceptance | Có | GPU container NOT VERIFIED |
| Tests | 288 passed / 1 warning | MEASURED | reports/task2/REVIEW2_STATUS_SUMMARY_VI.md | Không rerun trong docs | Có | KEY_NUMBERS 287 stale |
| CI | 39739640437 success at 4229a8b | MEASURED | https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39739640437 | Read-only API 2026-10-22 | Có | Docs mới chưa trong run |
| CD release | 39742439011 success v1.0.1 | MEASURED | https://github.com/IAmNDTK1230/MLLOps-Food_data/actions/runs/39742439011 | Read-only API 2026-10-22 | Có | Publication, không remote deployment |
| GHCR manifest | sha256:74ab5c8dd51f12a78e82f8b1806b968445e6318c16bae6ae5500d6b0b1b36d0a | MEASURED | ghcr.io/iamndtk1230/mllops-food_data:v1.0.1 | Read-only imagetools inspect | Có | linux/amd64 |

Nguồn: evidence cited per row. Loại: MIXED.

### Resolved Documentation Contradictions — Mâu thuẫn và cách xử lý

Bảng 2. Contradiction register

| Claim | Stale/ambiguous | Resolution | Evidence |
| --- | --- | --- | --- |
| KEY_NUMBERS ai_valid_count | 31694 bị dùng như số dòng AI hợp lệ | 33938 valid source rows; 31694 inference observations; 32457 distinct valid reviews | src/foody/cleaning.py; reports/foody_intelligence/cleaning.json |
| Hit@5/10 labels | Tên Hit nhưng formula chia cho số known positives | Giữ số gốc, ghi macro known-positive recall; binary Hit định nghĩa riêng | src/rag/evaluation.py; scripts/evaluate_rag_v3_retrieval.py |
| V2-A input | GAP_ANALYSIS/Q&A cũ gọi aspect-conditioned | V2-A text-only; V2-B ở src/aspect_conditioned là text+aspect | qwen_v2.yaml; qwen_aspect.yaml; reports/proposed_v2/protocol.json |
| Docker trạng thái cũ | FINAL_ARCHITECTURE/Q&A ghi daemon chưa chạy | DOCKER_ACCEPTANCE mới xác minh serving + pipeline exit0 | reports/task2/DOCKER_ACCEPTANCE.md |
| CI/CD trạng thái cũ | CICD_EVIDENCE mới nhất trong repo vẫn dừng v1.0.0 | Public API và registry xác nhận v1.0.1 tại 4229a8b; docs chưa nằm trong run đó | GitHub CI 39739640437; release 39742439011; GHCR digest |
| Test count | KEY_NUMBERS ghi 287 | Kết quả gần nhất 288 passed 1 warning, không chạy lại trong task docs | reports/task2/REVIEW2_STATUS_SUMMARY_VI.md; phiên acceptance trước |
| Luồng UI API | Sơ đồ gợi ý UI→API→Qwen | UI V3 gọi Python trực tiếp; API /ask là legacy parallel service | app/app.py; app/api.py |
| Qwen port/model | Config v1 và health API trỏ 1.5B; 3B local port8194 | Streamlit selected_v3_gateway dùng 3B; Compose URL override port8193 | config/demo.yaml; qwen_v3_3b.yaml; docker-compose.yml |
| Latency RAG | Các bảng có số khác nhau theo run | Tách shared policy run, V2 candidates, accepted replay, three-family replay và Docker CPU | reports/rag_v3/retrieval_policies.csv; reports/task2/FEASIBILITY.csv |
| Embedding chọn model | Một số mô tả dễ hiểu thành chưa từng benchmark | Có 2-model pool612 comparison; chưa exhaustive benchmark | reports/rag/embedding_comparison.csv |
| GPU configuration | gpu_layers=99 dễ bị coi là GPU verified | Requested khác observed; Docker CPU, GPU NOT VERIFIED | reports/task2/DOCKER_ACCEPTANCE.md |
| Causal mart guard | Tên policy dễ hiểu là causal analysis từ mart | Query route trả no hits/insufficient; không ước lượng causal effect | src/rag_v3/retriever.py; src/rag_v3/evidence.py |

Nguồn: code precedes old prose. Loại: SOURCE AUDIT.

## Unsupported information

Không có paper macro-F1 cùng filtered split; Foody gold accuracy; issue supervised accuracy; Kappa manual labeling mới; full-corpus relevance recall; exhaustive embedding search; controlled safety component-off effects; peak V1 inference resources bị mất; general population hallucination rate; GPU Docker assignment; remote production rollout; log đủ xác minh scenario push-rejected/rebase. Các mục này được ghi N/A, limitation hoặc EXAMPLE thay vì sáng tác.

## Parameter choices without controlled experiments

Bảng 3. Fixed choices

| Parameter | Value | Evidence / uncertainty |
| --- | --- | --- |
| max_features | 20000 | Không có sweep vocabulary size |
| min_df | 2 | Không có đối chứng min_df khác |
| sublinear_tf | True | Không có trial False |
| max_iter | 1500 | Không sweep iteration cap |
| Sentiment solver | lbfgs | Không so solver trong accepted baseline |
| Chunk policy | one review one document | Mô phỏng 128/0,128/32,256/0,256/32,512/0,512/64; không đánh giá index thay thế |
| Embedding dimensions | 384 | Potion có 256 nhưng là model khác |
| top_k | 5 demo; 10 retrieval evaluation | Không sweep 1/3/5/10 để chọn tối ưu demo |
| Dense và lexical top_n | 20 mỗi nhánh | Không sweep candidate depth |
| RRF constant | 60 | Không sweep k |
| BM25 k1 và b | SQLite FTS5: 1.2 và 0.75 | Code chỉ gọi bm25(table), không tune |
| Evidence reranking | +0.004 aspect; +0.006/-0.012 polarity; ±0.006 issue | Có policy comparison, không sweep riêng từng coefficient |
| Evidence packet cap | 3 review | Không sweep 1/3/5 |
| Packet text cap | 350 ký tự | Không so cap khác |
| Quantization | Q4_K_M | Không có full precision đối chứng |
| Temperature | 0 | Không sweep sampling temperature |
| Context length | 2048 | Không thử tối ưu context window |
| Output token cap | 32 sentiment; 128 V3 | Không sweep cap; DeepSeek structured output thất bại dưới 128 |
| Attempts | 2 | Không có retry budget comparison |
| CPU threads | 8 local config | Host 16 logical CPUs được nêu; không benchmark thread count |
| GPU layers | 99 requested; Docker CPU observed | Local launcher -CpuOnly đổi thành 0; Compose không khai báo GPU device |
| Ports | 8501 UI; 8000 API; 8193 Compose Qwen; 8194 local 3B | Không có bài toán quality optimization của port |
| Mount permissions | models/reports RO; data/state RW | Không benchmark permission; là deployment contract |
| Alert thresholds | n≥10; rate delta≥0.2; rating delta≤−1.0 | Không có threshold calibration trên gold alerts |

Nguồn: code/config registry. Loại: CONFIGURED.

## Repository inventory đã đọc

Bảng 4. src/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| src/__init__.py | N/A | N/A |
| src/api/__init__.py | N/A | N/A |
| src/api/app.py | create_app, lifespan, health, predict, monitoring | tests/test_sentiment_api.py |
| src/api/model_loader.py | LoadedModel, load_model | src/api/app.py, tests/test_sentiment_api.py |
| src/api/monitoring.py | InferenceMonitor, record, snapshot | src/api/app.py, tests/test_sentiment_api.py |
| src/api/schemas.py | PredictRequest, PredictResponse, nonblank | src/api/app.py |
| src/aspect_conditioned/__init__.py | N/A | N/A |
| src/aspect_conditioned/analysis.py | conflict_mask, recover_classical, subset_metrics, analyze | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, src/aspect_conditioned/runner.py, tests/test_aspect_conditioned.py |
| src/aspect_conditioned/prompts.py | input_payload, classical_input, choose_examples, immutable_json, freeze_prompts | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, src/aspect_conditioned/runner.py, src/aspect_conditioned/runtime.py, tests/test_aspect_conditioned.py |
| src/aspect_conditioned/runner.py | log_numbers, log_params, validate_records, predict_partition, classical_experiment, classical_test, finish, preserve_inference_protocol, run, features | scripts/recover_aspect_validation_reporting.py, src/ml/cli.py, tests/test_aspect_conditioned.py |
| src/aspect_conditioned/runtime.py | AspectRuntime, predict_aspect, AspectTransport, post | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, src/aspect_conditioned/runner.py, tests/test_aspect_conditioned.py |
| src/baselines/__init__.py | N/A | N/A |
| src/baselines/metrics.py | measure_predictions, scores, class_report, confusion_plot, comparison_plot, weight_plot | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/recover_aspect_validation_reporting.py, src/aspect_conditioned/runner.py, src/baselines/runner.py, src/proposed_v1/reporting.py, src/proposed_v1/runner.py, src/proposed_v2/analysis.py, src/proposed_v2/runner.py, tes |
| src/baselines/reporting.py | finalize_evidence, reject_constant | src/ml/cli.py, tests/test_food_baselines.py |
| src/baselines/rule_based.py | rule_definition, VietnameseRuleBased, score, predict | src/baselines/runner.py, tests/test_food_baselines.py |
| src/baselines/runner.py | load_protocol, environment, cached, run_rule, tracking_config, run_tfidf, failure_analysis, evaluate, run_all | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/recover_aspect_validation_reporting.py, scripts/verify_aspect_results.py, src/aspect_conditioned/runner.py, src/ml/cli.py, src/proposed_v1/reporting.py, src/proposed_v1/runner.py, src/proposed_v2/runner.py, tests/te |
| src/baselines/tfidf_logreg.py | select_validation_trial, build_pipeline | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/task2_classical_comparison.py, src/aspect_conditioned/runner.py, src/baselines/runner.py, tests/test_aspect_conditioned.py, tests/test_food_baselines.py |
| src/cli.py | main | N/A |
| src/config.py | Settings, clean_profile, safe_identifier, volume_root, from_env | scripts/shopee_visible_diagnostic.py, src/cli.py, src/crawler/shopee_products.py, src/databricks/client.py, src/databricks/jobs.py, src/databricks/preflight.py, src/databricks/uploader.py, src/orchestration/fixture_policy.py, src/orchestration/flow.py, src/orchestration/tasks.py, tests/test_acceptan |
| src/crawler/__init__.py | N/A | N/A |
| src/crawler/base.py | CrawlResult, CrawlStopped, TransientCrawlError, BaseCrawler, crawl | src/crawler/shopee_products.py, src/crawler/shopee_reviews.py, src/orchestration/flow.py, src/orchestration/tasks.py, tests/test_crawler.py, tests/test_flow.py |
| src/crawler/selectors.py | missing_cards_status, restriction, enrich_card | scripts/shopee_visible_diagnostic.py, src/crawler/shopee_products.py, tests/test_acceptance.py, tests/test_crawler.py |
| src/crawler/shopee_products.py | ShopeeProductCrawler, pace, check_page, fetch_page, crawl, monitor, worker | src/orchestration/tasks.py, tests/test_crawler.py |
| src/crawler/shopee_reviews.py | ShopeeReviewCrawler, crawl | src/orchestration/tasks.py |
| src/databricks/__init__.py | N/A | N/A |
| src/databricks/client.py | DatabricksAuthenticationError, workspace_client, check_connection | src/databricks/preflight.py, src/orchestration/tasks.py, tests/test_acceptance.py, tests/test_client.py |
| src/databricks/jobs.py | trigger_job | src/orchestration/tasks.py, tests/test_jobs.py |
| src/databricks/preflight.py | check_databricks, bootstrap_sql | src/cli.py, tests/test_acceptance.py |
| src/databricks/uploader.py | Uploader, remote_path, upload | src/orchestration/tasks.py, tests/test_acceptance.py, tests/test_flow.py, tests/test_uploader.py |
| src/demo.py | demo_config, demo_preflight, print_preflight, check, foody, model, chroma, bm25, qwen, marts, llmops | app/app.py, scripts/demo_launch_info.py, src/cli.py, src/rag_v3/cli.py, tests/test_demo_preflight.py |
| src/food/__init__.py | N/A | N/A |
| src/food/adapters.py | ordinal, adapt_vn_msasar, ExternalEvaluationAdapter, NTCSCVAdapter, VLSP2018RestaurantAdapter, adapt, adapt, adapt | src/food/data.py, tests/test_food_pipeline.py |
| src/food/analysis.py | distributions, rag_documents, token_summary, chunk_count, token_analysis, load_tokenizer, charts, analyze | src/ml/cli.py, tests/test_food_pipeline.py |
| src/food/config.py | FoodConfig, check, load | scripts/recover_aspect_validation_reporting.py, scripts/recover_qwen_reports.py, scripts/verify_aspect_results.py, src/ml/cli.py, tests/test_food_baselines.py, tests/test_food_pipeline.py |
| src/food/data.py | fetch, hub_metadata, read_source, import_dataset, source_data, prepare, load_prepared | src/food/analysis.py, src/food/split.py, src/ml/cli.py, tests/test_food_pipeline.py |
| src/food/interfaces.py | StructuredReviewAnalysis | src/food/analysis.py, tests/test_food_pipeline.py |
| src/food/split.py | leakage_groups, assign_splits, split_dataset, load_splits, find | src/baselines/reporting.py, src/baselines/runner.py, src/food/analysis.py, src/ml/cli.py, tests/test_food_pipeline.py |
| src/foody/__init__.py | N/A | N/A |
| src/foody/analytics.py | business_rows, aggregate, alerts, label_summary, build_mart | src/foody/pipeline.py, tests/test_foody_intelligence.py |
| src/foody/aspect.py | grouped_targets, scores, train | src/foody/enrichment.py, src/foody/pipeline.py, tests/test_foody_intelligence.py |
| src/foody/cleaning.py | snapshot, clean, prepare | src/foody/pipeline.py, tests/test_foody_intelligence.py |
| src/foody/enrichment.py | extract_issues, predict_observations, enrich, timing | src/foody/pipeline.py, tests/test_foody_intelligence.py |
| src/foody/pipeline.py | prepare_rag, protected_files, make_report, run_all, add_commands, run_command | N/A |
| src/foody/schema.py | normalize, digest, identity, restaurant_key, review_id, json_default, save_json, save_parquet | app/app.py, scripts/build_final_summary.py, scripts/build_rag_acceptance_report.py, scripts/build_rag_v2_review.py, scripts/create_rag_development.py, scripts/evaluate_rag_v2.py, scripts/evaluate_rag_v3_generation.py, scripts/evaluate_rag_v3_health.py, scripts/evaluate_rag_v3_retrieval.py, scripts/p |
| src/foody/validation.py | load_source, parse_date, validate_processed | scripts/verify_foody_intelligence.py, src/foody/cleaning.py, tests/test_foody_intelligence.py |
| src/foody_audit.py | write_json, inspect_encoding, distribution, duplicate_counts, timestamp_audit, label_audit, make_report, run, main, counts | src/foody_v2_audit.py, tests/test_foody_audit.py |
| src/foody_cleaning_preflight.py | checksum, write_json, source_inventory, require_canonical_restaurant_id, run, render_provenance, render_acceptance, main | tests/test_foody_preservation.py |
| src/foody_v2_audit.py | checksum, fraction, text_quality, parse_dates, restaurant_audit, readiness, search_provenance, run, render_reports, main | src/foody/cleaning.py, tests/test_foody_v2_audit.py |
| src/llm/__init__.py | N/A | N/A |
| src/llm/gateway.py | LLMGateway, name, version, generate | app/api.py, scripts/evaluate_rag_v3_generation.py, scripts/run_rag_v2_acceptance.py, scripts/task2_llm_benchmark.py, src/rag/cli.py, src/rag_v2/cli.py, src/rag_v3/cli.py, tests/test_rag_product.py |
| src/ml/__init__.py | N/A | N/A |
| src/ml/cli.py | add_commands, run_command | scripts/analyze_food_tokens.py, src/cli.py, tests/test_food_pipeline.py |
| src/ml/config.py | Experiment, MLConfig, TrackingConfig, valid_ngrams, valid_config, load, no_embedded_credentials, from_env | src/api/app.py, src/baselines/runner.py, src/foody/aspect.py, src/ml/data.py, src/ml/evaluate.py, src/ml/features.py, src/ml/labels.py, src/ml/mlflow_tracking.py, src/ml/registry.py, src/ml/split.py, src/ml/train.py, tests/test_ml_data.py, tests/test_ml_evaluation_registry.py, tests/test_ml_split.py |
| src/ml/data.py | load_provenance, read_input, nullable_text, normalize_rows, dataset_hash, data_report, prepare, import_dataset, require_trainable | src/ml/registry.py, src/ml/split.py, tests/test_ml_data.py |
| src/ml/evaluate.py | score_predictions, prediction_artifacts, evaluate_selected | src/ml/train.py, tests/test_ml_evaluation_registry.py, tests/test_ml_training.py |
| src/ml/features.py | normalize_text, build_pipeline | reports/aspect_conditioned/recovery_originals/posttest_analysis_before_fix.py, src/aspect_conditioned/analysis.py, src/baselines/rule_based.py, src/baselines/tfidf_logreg.py, src/food/adapters.py, src/food/split.py, src/ml/data.py, src/ml/split.py, src/ml/train.py, tests/test_ml_data.py, tests/test_ |
| src/ml/labels.py | label_rating | src/ml/data.py, tests/test_ml_data.py |
| src/ml/mlflow_tracking.py | configure_tracking | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/recover_aspect_validation_reporting.py, scripts/verify_aspect_results.py, src/aspect_conditioned/runner.py, src/baselines/runner.py, src/foody/aspect.py, src/ml/evaluate.py, src/ml/train.py, src/proposed_v1/reportin |
| src/ml/registry.py | register_selected | tests/test_ml_evaluation_registry.py |
| src/ml/split.py | leakage_groups, assign_splits, split_dataset, load_splits, find | src/ml/evaluate.py, src/ml/train.py, tests/test_ml_split.py |
| src/ml/train.py | train_experiments | tests/test_ml_training.py |
| src/models/__init__.py | N/A | N/A |
| src/models/crawl_run.py | CrawlRun | src/orchestration/flow.py, src/orchestration/tasks.py, src/storage/raw_writer.py, tests/test_cli_fixtures.py, tests/test_storage.py |
| src/models/product.py | Product, utc | src/processing/parquet_writer.py, src/processing/validator.py, tests/test_models.py |
| src/models/review.py | Review, utc | src/processing/parquet_writer.py, src/processing/validator.py, tests/test_models.py |
| src/orchestration/__init__.py | N/A | N/A |
| src/orchestration/fixture_policy.py | validate_fixture_mode | src/cli.py, src/orchestration/flow.py |
| src/orchestration/flow.py | PipelineFailed, shopee_data_pipeline, stage | src/cli.py |
| src/orchestration/report.py | execution_report | src/cli.py, tests/test_acceptance.py |
| src/orchestration/tasks.py | crawl_products, crawl_reviews, validate_data, write_raw_files, convert_to_parquet, upload_to_databricks, trigger_databricks_job, write_pipeline_summary | src/orchestration/flow.py |
| src/processing/__init__.py | N/A | N/A |
| src/processing/normalizer.py | number, normalize | src/processing/validator.py, tests/test_models.py, tests/test_normalizer.py |
| src/processing/parquet_writer.py | arrow_schema, write_parquet | src/orchestration/tasks.py, tests/test_storage.py |
| src/processing/validator.py | validate_records | src/orchestration/tasks.py, tests/test_storage.py, tests/test_validator.py |
| src/proposed_v1/__init__.py | N/A | N/A |
| src/proposed_v1/analysis.py | analyze | src/proposed_v1/reporting.py, src/proposed_v1/runner.py |
| src/proposed_v1/reporting.py | complete_saved | scripts/recover_qwen_reports.py |
| src/proposed_v1/runner.py | digest, freeze_prompts, select_prompt, score_predictions, usage, predict_partition, run | reports/aspect_conditioned/recovery_originals/posttest_analysis_before_fix.py, reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/recover_aspect_validation_reporting.py, scripts/verify_aspect_results.py, src/aspect_conditioned/analysis.py, src/aspect_conditioned/pro |
| src/proposed_v1/runtime.py | SentimentOutput, parse_output, messages, LocalQwen, unique_keys, sample_resources, predict | src/aspect_conditioned/runtime.py, src/llm/gateway.py, src/proposed_v1/reporting.py, src/proposed_v1/runner.py, src/proposed_v2/runner.py, tests/test_proposed_v1.py, tests/test_proposed_v2.py |
| src/proposed_v2/__init__.py | N/A | N/A |
| src/proposed_v2/analysis.py | csv_records, abstention_plot, diagnostic_rows, validation_analysis, protocol_documents, final_analysis | reports/aspect_conditioned/recovery_originals/posttest_analysis_before_fix.py, reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, src/aspect_conditioned/analysis.py, src/aspect_conditioned/runner.py, src/proposed_v2/runner.py, tests/test_proposed_v2.py |
| src/proposed_v2/examples.py | choose_examples, freeze_examples_and_prompts, has | src/proposed_v2/runner.py, tests/test_proposed_v2.py |
| src/proposed_v2/runner.py | TrackedRuntime, choose_candidate, historical_validation, frozen_inputs, assert_frozen, join_predictions, verified_records, finish, run, snapshot | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/recover_aspect_validation_reporting.py, scripts/verify_aspect_results.py, src/aspect_conditioned/runner.py, src/aspect_conditioned/runtime.py, src/ml/cli.py, src/proposed_v2/analysis.py, tests/test_proposed_v2.py |
| src/rag/__init__.py | N/A | N/A |
| src/rag/cli.py | portable_artifact_path, add_commands, selected_retriever, execute | app/api.py, scripts/build_rag_v2_review.py, scripts/evaluate_rag_v2.py, scripts/evaluate_rag_v3_retrieval.py, scripts/run_rag_v2_acceptance.py, scripts/verify_rag_filters.py, src/rag_v2/cli.py, src/rag_v3/retriever.py, tests/test_rag_product.py |
| src/rag/embeddings.py | EmbeddingSpec, LocalEmbeddings, documents, queries | src/rag/cli.py, src/rag/evaluation.py, tests/test_rag_product.py |
| src/rag/evaluation.py | known_positive_scores, development, pool_documents, model_files, compare_candidates, evaluate_index | scripts/build_rag_v2_review.py, scripts/evaluate_rag_v2.py, scripts/evaluate_rag_v3_retrieval.py, src/rag/cli.py, tests/test_rag_product.py |
| src/rag/monitoring.py | record, summary | app/app.py, scripts/build_rag_acceptance_report.py, src/llm/gateway.py, src/rag/retriever.py, src/rag/service.py, src/rag_v2/health.py, src/rag_v2/service.py, src/rag_v3/health.py, src/rag_v3/service.py, tests/test_rag_product.py, tests/test_rag_v3.py |
| src/rag/retriever.py | where_filter, Retriever, search | src/rag/cli.py, src/rag/evaluation.py, src/rag_v2/hybrid.py, src/rag_v2/lexical.py, tests/test_rag_product.py |
| src/rag/schemas.py | RetrievalRequest, ReviewHit, Evidence, GroundedAnswer, HealthReport, ordered_dates | app/api.py, app/app.py, scripts/build_rag_v2_review.py, scripts/evaluate_rag_v2.py, scripts/evaluate_rag_v3_generation.py, scripts/evaluate_rag_v3_retrieval.py, scripts/run_rag_v2_acceptance.py, scripts/verify_rag_filters.py, scripts/verify_rag_v2_filters.py, src/rag/cli.py, src/rag/evaluation.py, s |
| src/rag/service.py | DraftAnswer, resolve_restaurant, prompt, context, check_refs, insufficient, answer_question, health_report | app/api.py, scripts/run_rag_v2_acceptance.py, scripts/verify_rag_v2_filters.py, src/demo.py, src/rag/cli.py, src/rag_v2/cli.py, src/rag_v2/health.py, src/rag_v2/service.py, src/rag_v3/cli.py, src/rag_v3/health.py, src/rag_v3/service.py, tests/test_rag_product.py, tests/test_rag_v2.py, tests/test_rag |
| src/rag/vector_store.py | read_documents, epoch, chroma_metadata, client, collection_name, open_collection, build_index | scripts/create_rag_development.py, scripts/task2_rag_accounting.py, scripts/verify_rag_filters.py, scripts/verify_rag_index.py, src/demo.py, src/rag/cli.py, src/rag/evaluation.py, src/rag/retriever.py, src/rag_v2/lexical.py, tests/test_rag_product.py, tests/test_rag_v2.py |
| src/rag_v2/__init__.py | N/A | N/A |
| src/rag_v2/cli.py | add_commands, selected_v2_retriever, execute | scripts/run_rag_v2_acceptance.py, scripts/verify_rag_v2_filters.py |
| src/rag_v2/health.py | health_report_v2, accepted | src/rag_v2/cli.py |
| src/rag_v2/hybrid.py | RetrievalConfig, effective_request, rrf_fuse, HybridRetriever, search, search_debug | scripts/build_rag_v2_review.py, scripts/evaluate_rag_v2.py, scripts/evaluate_rag_v3_retrieval.py, src/rag_v2/cli.py, src/rag_v3/retriever.py, src/rag_v3/routing.py, tests/test_rag_v2.py |
| src/rag_v2/intent.py | QueryIntent, detect, evidence_compatible, issue_matches | src/rag_v2/health.py, src/rag_v2/hybrid.py, src/rag_v2/service.py, src/rag_v3/evidence.py, src/rag_v3/routing.py, tests/test_rag_v2.py |
| src/rag_v2/lexical.py | search_terms, match_expression, build_index, BM25Retriever, search | scripts/build_rag_v2_review.py, scripts/evaluate_rag_v2.py, scripts/evaluate_rag_v3_retrieval.py, src/rag_v2/cli.py, src/rag_v2/hybrid.py, src/rag_v3/retriever.py, tests/test_rag_v2.py |
| src/rag_v2/service.py | Claim, GroundedAnswerV2, support_gate, validate_claim, answer_question_v2 | scripts/run_rag_v2_acceptance.py, src/rag_v2/cli.py, src/rag_v2/health.py, src/rag_v3/evidence.py, tests/test_rag_v2.py |
| src/rag_v3/__init__.py | N/A | N/A |
| src/rag_v3/cli.py | selected_v3_gateway, add_commands, execute | app/app.py, scripts/evaluate_rag_v3_health.py, scripts/run_rag_v3_health.py |
| src/rag_v3/evidence.py | Packet, build_packet, evidence_for_refs, validate_packet_citations, extractive_answer, generation_payload | scripts/evaluate_rag_v3_generation.py, src/rag_v3/health.py, src/rag_v3/service.py, tests/test_rag_v3.py |
| src/rag_v3/health.py | health_report_v3 | app/app.py, scripts/evaluate_rag_v3_health.py, scripts/run_rag_v3_health.py, src/rag_v3/cli.py, tests/test_rag_v3.py |
| src/rag_v3/retriever.py | RoutedRetriever, search_debug | app/app.py, scripts/evaluate_rag_v3_health.py, scripts/evaluate_rag_v3_retrieval.py, scripts/run_rag_v3_health.py, src/rag_v3/cli.py |
| src/rag_v3/routing.py | Route, route_query | scripts/evaluate_rag_v3_generation.py, scripts/evaluate_rag_v3_retrieval.py, src/rag_v3/health.py, src/rag_v3/retriever.py, src/rag_v3/service.py, tests/test_rag_v3.py |
| src/rag_v3/service.py | V3Draft, V3Claim, GroundedAnswerV3, attach_citation, prepare_question, answer_question_v3 | app/app.py, scripts/evaluate_rag_v3_generation.py, scripts/summarize_rag_v3.py, scripts/task2_llm_benchmark.py, src/rag_v3/cli.py, src/rag_v3/health.py, tests/test_rag_v3.py |
| src/storage/__init__.py | N/A | N/A |
| src/storage/manifest.py | atomic_json, UploadManifest, read, contains, add | reports/aspect_conditioned/recovery_originals/posttest_analysis_before_fix.py, reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/browser_smoke.py, scripts/recover_aspect_validation_reporting.py, scripts/setup_qwen_v1.py, scripts/shopee_visible_diagnostic.py, src/as |
| src/storage/raw_writer.py | write_jsonl, write_raw | src/orchestration/tasks.py, src/processing/validator.py, tests/test_storage.py |
| src/utils/__init__.py | N/A | N/A |
| src/utils/hashing.py | file_checksum, text_hash | reports/aspect_conditioned/recovery_originals/posttest_runner_before_fix.py, scripts/recover_aspect_validation_reporting.py, scripts/setup_qwen_v1.py, scripts/task2_classical_comparison.py, scripts/task2_llm_benchmark.py, src/api/model_loader.py, src/aspect_conditioned/runner.py, src/baselines/repor |
| src/utils/logging.py | JsonFormatter, configure_logging, event, format | src/crawler/shopee_products.py, src/databricks/uploader.py, src/orchestration/flow.py |
| src/utils/retry.py | transient | src/databricks/client.py, src/databricks/uploader.py, tests/test_retry.py |
| src/utils/timestamps.py | utc_now | scripts/shopee_visible_diagnostic.py, src/api/monitoring.py, src/crawler/shopee_products.py, src/databricks/uploader.py, src/ml/data.py, src/models/crawl_run.py, src/orchestration/flow.py, src/processing/parquet_writer.py, src/processing/validator.py, src/storage/raw_writer.py, src/utils/logging.py |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 5. app/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| app/__init__.py | N/A | N/A |
| app/api.py | Question, health, ask, report | tests/test_rag_product.py |
| app/app.py | table, json_file, available, choose_restaurant, date_filter, restaurant_page, explorer_page, analyst_page, monitor_page, main | tests/test_rag_product.py |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 6. scripts/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| scripts/__init__.py | N/A | N/A |
| scripts/analyze_food_tokens.py | main | N/A |
| scripts/browser_smoke.py | smoke | N/A |
| scripts/build_final_summary.py | read, row_by, test_count, build | N/A |
| scripts/build_rag_acceptance_report.py | read, run | N/A |
| scripts/build_rag_v2_review.py | describe, main | N/A |
| scripts/create_rag_development.py | create | N/A |
| scripts/demo_launch_info.py | main | N/A |
| scripts/evaluate_rag_v2.py | main | src/rag_v2/cli.py |
| scripts/evaluate_rag_v3_generation.py | ReplayRetriever, load_frozen_packets, main, search_debug | scripts/task2_llm_benchmark.py, src/rag_v3/cli.py, tests/test_rag_v3.py |
| scripts/evaluate_rag_v3_health.py | main | N/A |
| scripts/evaluate_rag_v3_retrieval.py | main | src/rag_v3/cli.py |
| scripts/prepare_qwen_v3_3b.py | main | N/A |
| scripts/preserve_foody_source.py | digest, preserve, main | src/foody_cleaning_preflight.py, tests/test_foody_preservation.py |
| scripts/recover_aspect_validation_reporting.py | main | N/A |
| scripts/recover_qwen_reports.py | main | N/A |
| scripts/run_rag_v2_acceptance.py | main | N/A |
| scripts/run_rag_v3_health.py | main | N/A |
| scripts/setup_qwen_v1.py | download, main | N/A |
| scripts/shopee_visible_diagnostic.py | public_resource, safe_url, safe_message, classify, diagnose, response_event, capture | tests/test_visible_diagnostic.py |
| scripts/smoke_streamlit_rag.py | main | N/A |
| scripts/smoke_streamlit_rag_v3.py | main | N/A |
| scripts/start_demo.cmd | N/A | N/A |
| scripts/start_demo.ps1 | N/A | N/A |
| scripts/summarize_rag_v3.py | failure_class, main | N/A |
| scripts/task2_build_evidence.py | read_json, read_csv, write_csv, save, bar, main | N/A |
| scripts/task2_classical_comparison.py | metrics, write_csv, main, fmt | N/A |
| scripts/task2_finalize_evidence.py | data, csv_rows, csv_write, plot_save, reconcile_llm, feasibility, llm_report, architecture, checklist, main, add | N/A |
| scripts/task2_llm_benchmark.py | paths_for, analyze, main | N/A |
| scripts/task2_rag_accounting.py | write_csv, summary, policy_measure, main | N/A |
| scripts/task2_render_rag_ablation.py | main | N/A |
| scripts/verify_aspect_results.py | main | N/A |
| scripts/verify_foody_audit.py | main | N/A |
| scripts/verify_foody_intelligence.py | main | N/A |
| scripts/verify_foody_v2_audit.py | main | N/A |
| scripts/verify_rag_filters.py | main | N/A |
| scripts/verify_rag_index.py | main | N/A |
| scripts/verify_rag_v2_filters.py | main | N/A |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 7. tests/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| tests/conftest.py | product | N/A |
| tests/test_acceptance.py | configured, test_missing_cards_status, test_preflight_uses_profile_without_pat, test_preflight_missing_unified_auth_reports_safe_failure, test_preflight_write_verify_and_cleanup, test_preflight_failure_redacts_exception_and_stops, test_preflight_read_failure_still_cleans_own_file, test_bootstrap_uses_custom_configuration, test_report_never_invents_cloud_counts, test_uploader_rejects_shallow_and_outside_paths, test_bundle_graph_and_python_files, check_no_classic_compute | N/A |
| tests/test_aspect_conditioned.py | rows, test_only_whitelisted_aspect_input, test_train_only_selector_deterministic_conflicting_pair, test_aspect_token_preserved_in_tfidf_vocabulary, test_runtime_transport_supplies_text_and_aspect_only_and_restores_session, test_checkpoint_binds_aspect_not_just_text, test_inflight_test_request_is_not_repeated, test_conflict_membership_and_historical_recovery_without_inference, test_selection_uses_validation_macro_f1, test_report_only_recovery_pins_sources_and_preserves_inference, test_posthoc_reindex_preserves_sample_identity | N/A |
| tests/test_cli_fixtures.py | invoke, test_cloud_fixture_requires_explicit_allow_flag, test_cloud_fixture_rejects_any_catalog_other_than_exact_test, test_cloud_fixture_allowed_only_with_flag_and_test_catalog, test_crawl_only_fixture_remains_allowed, test_fixture_upload_only_combination_rejected, run | N/A |
| tests/test_client.py | test_explicit_profile_has_priority_over_legacy_pat, test_default_unified_auth_without_pat, test_legacy_pat_only_after_default_configuration_failure, test_invalid_explicit_profile_never_falls_back_and_hides_sdk_context, test_no_credentials_failure_is_sanitized | N/A |
| tests/test_config.py | test_normal_default_catalog, test_token_excluded_from_serialization, test_profile_loaded_from_environment_without_pat, test_unsafe_names_rejected, test_blank_prefect_api_url_is_unset | N/A |
| tests/test_crawler.py | test_restrictions, test_card_identity, test_stop_prevents_next_navigation, test_auth_redirect_stops_before_dom_wait, test_resume_only_fetches_missing_pages, check, check | N/A |
| tests/test_databricks_merge.py | helper, test_first_write_uses_append_and_never_merges, test_existing_table_preserves_insert_only_merge, serverless_mode | N/A |
| tests/test_demo_preflight.py | test_active_demo_configuration_is_v3_3b, test_frozen_demo_artifacts_pass_read_only_preflight | N/A |
| tests/test_flow.py | unwrap_tasks, test_offline_flow_preserves_bad_rows, test_blocked_keeps_partial_raw_and_skips_upload, test_stage_failure_writes_summary, test_direct_flow_cannot_bypass_fixture_safety, test_test_catalog_fixture_executes_upload_and_job_with_isolated_outputs, upload | N/A |
| tests/test_food_baselines.py | test_fixed_rule_polarity_negation_and_boundaries, test_longest_phrase_counted_once_and_intensifiers_documented, test_tfidf_fit_vocabulary_only_from_training_text, test_selection_uses_validation_only_and_stable_ties, test_latency_does_not_predict_test_samples_twice, test_macro_metrics_include_all_three_classes, test_protocol_rejects_different_split_without_resplitting, cached_setup, test_attempted_test_evaluation_never_retries, test_completed_evaluation_returns_evidence_without_predictions, test_failure_outputs_preserve_predictions_and_actual_as | N/A |
| tests/test_food_pipeline.py | config, source_rows, imported, test_adapter_gold_labels_filters_cleaning_rejections_duplicates, test_missing_required_schema_is_explicit, test_failed_download_provides_manual_instructions_without_substitution, test_manual_schema_mismatch_cannot_be_imported_as_food, test_import_provenance_and_tamper_checks, test_raw_tamper_and_missing_source_fail, test_transitive_review_and_text_grouping, test_shared_deterministic_splits_no_leakage, test_chunk_count_boundaries, test_rag_metadata_keeps_aspect_sentiment_alignment, test_analysis_outputs_actual_unit | N/A |
| tests/test_foody_audit.py | source_csv, execute, test_utf8_vietnamese_is_not_misclassified_due_to_excel, test_legacy_loss_indicators_and_unknown_labels_block_training, test_legacy_encoding_alone_is_not_proof_of_corruption, test_utf8_bom_and_actual_replacement_character_distinguished, test_duplicate_denominators_distinguish_missing_keys, test_dates_missing_and_invalid_are_retained_separately, test_label_association_is_not_presented_as_annotation_provenance, test_outputs_cannot_contain_immutable_source | N/A |
| tests/test_foody_intelligence.py | source, test_keys_and_review_ids, test_cleaning_preserves_rows_and_semantics, test_dates, test_utf8_snapshot, test_external_schema_rejected, SentimentStub, AspectStub, test_inference_only_valid_deduplicated_text, test_issue_gates_and_negation, enriched, test_mart_counts_actual_reviews_not_inference_groups, monthly_row, test_alert_sample_rules_and_calendar_comparability, test_aspect_grouping_and_leakage_guard, test_rag_metadata_and_invalid_exclusion, predict_proba, predict_proba | N/A |
| tests/test_foody_preservation.py | example_bytes, test_snapshot_is_byte_identical_and_preserves_raw_fields, test_snapshot_rerun_verifies_without_rewriting_manifest_or_copy, test_existing_snapshot_is_never_overwritten_on_source_change, test_mismatched_expected_hash_does_not_create_snapshot, test_incomplete_snapshot_pair_is_not_silently_repaired, test_snapshot_cannot_replace_source, test_invalid_utf8_is_not_silently_reencoded, test_statistics_or_column_order_cannot_bypass_provenance_gate, test_preflight_stops_without_creating_processed_data_or_renaming_labels | N/A |
| tests/test_foody_v2_audit.py | test_utf8_quality_distinguishes_replacement_from_question_punctuation, test_duplicate_restaurant_headers_are_not_silently_coalesced, test_explicit_date_suffix_parsing_keeps_raw_values, test_unknown_labels_do_not_block_demo_rag_after_cleaning, test_provenance_search_does_not_turn_correlation_or_reader_code_into_derivation, test_indicator_rates_expose_denominators_without_fabricated_zero | N/A |
| tests/test_jobs.py | test_wait_for_job_success_and_idempotency, test_failed_remote_job_is_not_success, test_missing_job_explicitly_skipped | N/A |
| tests/test_manifest.py | test_destination_and_checksum_both_required | N/A |
| tests/test_ml_data.py | test_vietnamese_normalization_preserves_accents, test_rating_baseline, test_configurable_label_rule, test_row_mapping_rejections_and_exact_duplicates, test_missing_columns_and_invalid_dataset_fail, test_trainability_rejects_invalid_or_single_labels, test_import_roundtrip_and_tamper_detection, test_no_dataset_and_fixture_rejected_before_training | N/A |
| tests/test_ml_evaluation_registry.py | test_selected_test_set_evaluated_once, test_registry_records_provenance_but_never_promotes_alias | N/A |
| tests/test_ml_split.py | test_deterministic_product_and_text_leakage_protection, test_duplicate_comments_connect_different_products, test_too_few_independent_groups_fails | N/A |
| tests/test_ml_training.py | test_feature_pipeline_configuration_without_fitting, test_selection_uses_validation_only_and_tracks_three_experiments, test_training_without_imported_dataset_fails_before_fit, test_binary_macro_metric_uses_present_classes | N/A |
| tests/test_models.py | test_utc_and_optional_fields, test_invalid_product, test_review_bounds | N/A |
| tests/test_normalizer.py | test_number, test_ambiguous_numbers_rejected, test_fractional_counts_rejected | N/A |
| tests/test_proposed_v1.py | test_strict_json_labels, test_invalid_output_never_silently_mapped, test_request_contains_text_only, test_prompt_examples_train_only_and_hashed, test_validation_selection_and_tie_breaks, test_invalid_terminal_output_counts_as_error, test_completed_rows_checkpointed_no_second_inference, test_unknown_inflight_test_request_cannot_repeat, test_invalid_json_retry_and_accounting, Spy, Response, Session, predict, raise_for_status, json, post | N/A |
| tests/test_proposed_v2.py | train_rows, test_selector_train_only_reproducible_all_contrasts, test_heldout_fallback_and_english_example_prohibited, test_prompt_counts_hashes_and_inference_contract, test_macro_f1_selection_beats_neutral_recall_only, test_join_preserves_nonconsecutive_indices_and_gold, test_frozen_inputs_audited_without_writing, test_incomplete_or_duplicate_checkpoint_not_finalized, test_posthoc_flags_not_inference_features, test_external_and_aspect_protocol_proposals_only | N/A |
| tests/test_rag_product.py | FakeEmbeddings, test_saved_windows_artifact_path_resolves_portably, make_documents, test_vector_persistence_filters_and_retrieval, test_document_validation_excludes_invalid, test_retrieval_contract_and_known_positive_scope, fake_hit, FakeRetriever, FakeGateway, test_grounded_answer_and_empty_retrieval, test_health_schema, test_health_report_uses_marts_and_review_ids, test_gateway_json_contract, test_monitor_logs_no_raw_text, test_streamlit_and_api_import_smoke, documents, queries, search, generate, Reply, Session, raise_for_status, json, post | N/A |
| tests/test_rag_v2.py | hit, test_bm25_index_and_metadata_filters, test_rrf_fusion_and_v1_v2_separation, test_intent_detection_and_positive_service_rejection, test_claim_membership_topic_and_mixed_evidence, FakeDense, FakeLexical, FakeGateway, test_hybrid_filter_and_insufficient_evidence, test_insufficient_no_generation, search, search, generate, EmptyRetriever, search_debug | N/A |
| tests/test_rag_v3.py | hit, FakeRetriever, FakeGateway, no_operational_log, test_query_routing, test_packet_deduplicates_and_does_not_grant_frequency, test_late_complaint_is_preserved_verbatim_in_packet, test_programmatic_citation_maps_to_exact_review_and_checks_clauses, test_one_citation_cannot_cover_second_unsupported_service_fact, test_frequency_claim_requires_aggregate_support, test_generation_replays_exact_same_saved_packets_for_models, test_minimal_generation_schema_rejects_extra_fields, test_food_generation_failure_uses_traceable_extractive_fallback, test_pric | N/A |
| tests/test_retry.py | test_retry_only_cloud_transient_errors | N/A |
| tests/test_sentiment_api.py | test_prediction_probabilities_version_and_private_text_not_logged, test_no_model_returns_unavailable_without_secret_details, test_mlflow_configuration_never_falls_back_to_local | N/A |
| tests/test_storage.py | test_history_and_parquet_schema | N/A |
| tests/test_uploader.py | test_upload_once_and_recover_missing_manifest, test_remote_collision_never_overwrites | N/A |
| tests/test_validator.py | test_rejections_preserve_record_and_error | N/A |
| tests/test_visible_diagnostic.py | snapshot, test_outcome_requires_evidence, test_caught_console_error_does_not_establish_javascript_failure, test_navigation_failure, test_dynamic_and_private_resources_excluded | N/A |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 8. databricks/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| databricks/00_setup.py | main | N/A |
| databricks/01_bronze_products.py | N/A | N/A |
| databricks/02_bronze_reviews.py | N/A | N/A |
| databricks/03_silver_products.py | N/A | N/A |
| databricks/04_silver_reviews.py | N/A | N/A |
| databricks/05_gold_product_metrics.py | N/A | N/A |
| databricks/06_gold_review_dataset.py | N/A | N/A |
| databricks/common.py | Runtime, schema, bronze, parsed, merge_insert, validity, silver, gold_products, gold_reviews, table, landing | N/A |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 9. .github/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| .github/workflows/ci.yml | N/A | N/A |
| .github/workflows/release.yml | N/A | N/A |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 10. config/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| config/demo.yaml | N/A | N/A |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

Bảng 11. docs/experiments/

| File | Main symbols | Caller modules |
| --- | --- | --- |
| docs/experiments/ASPECT_CONDITIONED.md | N/A | N/A |
| docs/experiments/BASELINES.md | N/A | N/A |
| docs/experiments/PHASE2.md | N/A | N/A |
| docs/experiments/PROPOSED_V1.md | N/A | N/A |
| docs/experiments/PROPOSED_V2.md | N/A | N/A |

Nguồn: AST inventory static. Loại: SOURCE AUDIT.

## Report evidence coverage

- reports/final/CICD_ACCEPTANCE.md — SHA256 e85706a0143e72846ebe012f779fb16354d1d81f067f3488b444586d81b3e2e7
- reports/final/DEMO_BACKUP_PLAN.md — SHA256 5ae4c5a3737d735eba4817b0884e2318ad1a77f3b0b63cdbb69065e131473c98
- reports/final/DEMO_SCRIPT_VI.md — SHA256 8992c9fa655587edae4530003d52198e7b329792c36e86d8c006b137c77b6a7f
- reports/final/FINAL_ARCHITECTURE.md — SHA256 1d1a682a0250292bbd6a8c34afcced5f99c2a3eadebcec1e9ee44cc9f9008011
- reports/final/FINAL_DEMO_ACCEPTANCE.md — SHA256 4002ddd61c6a67b7d1ebda7c291b531d7be6308ad93f9bd919e7cc77109431be
- reports/final/KEY_NUMBERS.json — SHA256 55982c5c24d8a488645b24ad8837b99dedfcb900696532c11b222867e10d38ff
- reports/final/MODEL_COMPARISON.csv — SHA256 3908367d47cec39e261cfddb1fa466e7ae9f1138c8cdb2d46e6f2c7d8b86821e
- reports/final/RAG_V3_ACCEPTANCE_REPORT.md — SHA256 31e708945e95ee8f334d3e3cfe307664a01d06a7e3f3b5c0fc3976f2797c906e
- reports/final/TASK2_EXPERIMENT_STORY.md — SHA256 8c7511995c89e210940b1a14e5312a44d0530d96bdb983ebce2f28a524fe971b
- reports/task2/BASELINE_STABILITY.md — SHA256 4ebd198328abb5eec66f07724189848ed60c5eebbb605762c2b79a9a6bd505dc
- reports/task2/baseline_three_seed.csv — SHA256 ae07cb53c8be4d0a4f5df0fe4b9e10b797a778279e5d67858acb770759b8fbb7
- reports/task2/chunking_comparison.csv — SHA256 eea8d3aada3f9f657946f6e89554a61cbacf2a74d51a4c065c1c274e7f77fba5
- reports/task2/CHUNKING_DECISION.md — SHA256 128dd339147fece61ff08043e75c39de8141a1258d0c409a606e3b9544c976c0
- reports/task2/CICD_EVIDENCE.md — SHA256 085eda63935d0b0af9df5a6692ec1119053cd4975ef737a208c406efb3858988
- reports/task2/class_distribution.csv — SHA256 6ba6345671efc56b2cd6e4f5bef53fa7700779523581c47dee45d49f89866393
- reports/task2/classical_model_comparison.csv — SHA256 3edbb67dc12c0c3a7d95efc7d6b6e7f99617bd7651fc978da4e54b223e601f3d
- reports/task2/CLEANING_FLOW.md — SHA256 17a024111ad77d08017fd17c5a6c93e631e8ecf0407ea0d648e872085aa09ebb
- reports/task2/dataset_sources.csv — SHA256 e567fb654431d0d7df2f676f9f9303e26b479f789ffdd16f862877addb3d9e86
- reports/task2/DATASET_SUMMARY.md — SHA256 6c6fcef06c4e3c188c2b63a1a9490c87892a298c4f83d6d8b11bbb7e8b01d517
- reports/task2/DOCKER_ACCEPTANCE.md — SHA256 600e717ea2fbdf850da9f00127e941248dfce927cbaae64f541a288367f7e932
- reports/task2/embedding_workload.csv — SHA256 8ba6ba1f31f1670a90b57cd15253a714d7acae075a51c080ce3ce380c8eb97ee
- reports/task2/failure_counts.csv — SHA256 21de2279e4dc49f2c8ed0e3fd6038ebe6c366d0ffcb57347e80cba3338d9ecf3
- reports/task2/FAILURE_TAXONOMY.md — SHA256 d9c34cb87b2971a96c532406a87e298d1be38bff0f0fedfc0bfa0c406ec4bb41
- reports/task2/FEASIBILITY.csv — SHA256 850894db8b4dcd146abd7c454c4f29352c588a58803bd6e1904350dd37c24fa1
- reports/task2/GAP_ANALYSIS.md — SHA256 39a54c602fbe08994720b75cd57b402365d14ae7dc2d0ae6d301bad2b83b9aeb
- reports/task2/imbalance_comparison.csv — SHA256 53ef138a8a9680eff63d54c1212f18137e604b8a1bd9d55e62ac140db515fac5
- reports/task2/linearsvc_validation_selection.csv — SHA256 f2fe1010c21ba90b22ef46bf621f07354671656730596bc68abf65c96540b877
- reports/task2/LLM_BENCHMARK.md — SHA256 b4c61dd72d1c81c9a63a65f5e934db3a7f928bb3b6438d96ef4b95cb37212f9a
- reports/task2/llm_benchmark_provenance.json — SHA256 5a2b502ebfd62003ed1b238aa0d8df3d9536d997aec4ebdaf63b910d0e41f4c3
- reports/task2/llm_comparison.csv — SHA256 45025a35d9fff8abb1d650cee05f03e27967e186a6a6bbe673fd456434dcdfa1
- reports/task2/MICROSERVICE_ARCHITECTURE.md — SHA256 c3dcb33e3d9d86201782eeef5d8a000ea6aa9068b4984a2b55bf00d86672b807
- reports/task2/paper_vs_group.csv — SHA256 38306d2e20d55fc7616d0faf2777f42f8bfaede5a185a454f2bf6e1975c0863a
- reports/task2/PAPER_VS_GROUP.md — SHA256 9064fc14d2f47268d1ce42c7e07259a197c9118f93ee84e26da8a5756ee488cb
- reports/task2/RAG_ABLATION.csv — SHA256 299521653954b8fea66f2e5b3073c8ab4ca497e920844f62fd6ea599acf7622c
- reports/task2/RAG_ABLATION.md — SHA256 fedb65a2eae9f8e441a813f1b7d5573c9f64e4432b7bf7dc225fdd652e7fd525
- reports/task2/RAG_ABLATION_FINAL.csv — SHA256 a8b67a8c4b384792e1c3fd90ce648c4800d7423f238d1aaa4ab73d85a29ff75c
- reports/task2/RAG_ABLATION_FINAL.md — SHA256 d5c5901d4f3dd2f439886db38f005b42f271dc9e077690a45af2a8bca24ec768
- reports/task2/RAG_METADATA_SCHEMA.md — SHA256 1e2a6672e211c774db0732bf8fd2273ce4f8026338ba6973c957b3f3aa9092bd
- reports/task2/rag_token_distribution.csv — SHA256 b46c3e797394972b04c09f1118908e26a665d638fbb5365aebaa42f333278985
- reports/task2/rag_token_statistics.json — SHA256 3727244397c7e33d6afa1cd4834355f120997e3816e6ff168604c3db6bd7e156
- reports/task2/REVIEW2_QA_VI.md — SHA256 b16ce2785c043d9d041b2ad18da13b244938b06d60ad4005c24c598889af4b94
- reports/task2/REVIEW2_STATUS_SUMMARY_VI.md — SHA256 ecf0b60b34b6b62e9eea8c87f2f8880a3544f13158ad63236fa9fb93a88bbe3c
- reports/task2/TASK2_GAP_MATRIX.md — SHA256 bec4baf0918525b426ec096d0e24b910f99ac2d7ded0bd476f3ac2c84c1dce6e
- reports/task2/TASK2_SELF_ASSESSMENT.md — SHA256 4a5f3969c4386bd952bacac833c0e78bd0ddc66fa0111043205f66b169dc51d4
- reports/task2/TOKEN_NOTE.md — SHA256 fb5f5026b8d89f38080b9db246724016257a3ccef4d8b5eacaba438d170b4607
- reports/task2/TRAINING_SCOPE.md — SHA256 85fb610a2e4a8a7312a56225bfad0775ecc966817eaa1722e5c2b1465f110d15

## Quality verification

Hai DOCX được mở bằng `python-docx` và Microsoft Word, xuất PDF để kiểm tra bố cục. Hướng dẫn dài **102 trang**, báo cáo **38 trang** theo Word. Contact sheets từ toàn bộ 140 trang đã được xem để phát hiện trang trống bất thường, bảng tràn, hình mất, chữ bị cắt và dấu tiếng Việt lỗi; không thấy lỗi đó trong bản render. Trường mục lục được chèn và cấu hình cập nhật khi mở tài liệu; người đọc có thể dùng **Update entire table** trong Word nếu số trang thay đổi trên máy khác. Công cụ render LibreOffice đi kèm không chạy vì máy không có `soffice.exe`, nên dùng Word đã cài để xác định số trang.

Kiểm tra cấu trúc: hướng dẫn 85 chương, 46 bảng, 11 hình, 30 công thức và 60 câu hỏi; báo cáo 30 mục đánh số, 30 bảng, 8 hình, 30 công thức và 12 câu hỏi phụ lục. Tất cả 19 liên kết hình Markdown trỏ tới file hiện hữu; DOCX có đúng 19 hình nhúng. Không phát hiện U+FFFD trong Markdown hoặc cú pháp ảnh Markdown còn lộ trong DOCX. Sổ tay có 32 thẻ bảo vệ tham số.

Đối chiếu SHA-256 cuối cùng với snapshot trước khi tạo tài liệu: **701/701 file protected không đổi**. Phạm vi bao gồm source, app, tests, config, Docker/workflow, các báo cáo nghiệm thu, data và model được liệt kê bởi script audit; không có source, data, model hay index nào được generator ghi. `git status` chỉ xuất hiện sáu đầu ra dưới `docs/` và các script dưới `scripts/documentation/`. Các PDF/ảnh kiểm tra nằm trong `.qa` tạm, không phải deliverable.
