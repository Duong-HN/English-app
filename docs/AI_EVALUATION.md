# Đánh giá chất lượng AI

## Mục tiêu

Nhánh này bổ sung cơ sở để đánh giá AI một cách trung thực. Test schema hoặc mock provider chỉ chứng minh contract kỹ thuật; chúng không chứng minh feedback có chính xác hoặc hữu ích cho người học.

## Bộ dữ liệu

File [ai_cases.jsonl](../backend/evaluation/ai_cases.jsonl) chứa 30 mẫu đại diện cho:

- writing;
- reading;
- speaking transcript;
- trình độ A2 đến C1;
- câu đúng và câu có lỗi;
- input ngắn, dài, ngoài chủ đề và rỗng;
- grammar, vocabulary, relevance, grounding và academic reasoning.

Các case hiện chỉ là input và focus mong muốn. Không được xem chúng là kết quả đánh giá đã hoàn thành.

## Rubric cho người đánh giá

Mỗi kết quả AI cần được một reviewer chấm theo thang 1–5:

| Trường | Ý nghĩa |
|---|---|
| correctness | AI có phát hiện đúng vấn đề không |
| usefulness | Feedback có giúp người học sửa bài không |
| level_fit | Feedback có phù hợp trình độ không |
| grounding | Feedback có bám input/context không |
| hallucination | Có tuyên bố sai hoặc không có bằng chứng không |

Review JSONL cần có các trường:

    case_id
    reviewer_id
    correctness
    usefulness
    level_fit
    grounding
    hallucination

Prototype API workflow:

- `POST /api/v1/admin/ai-evaluations` stores one review linked to a persisted `analysis_id`.
- The same administrator can update their review without creating a duplicate row.
- `GET /api/v1/admin/ai-evaluations/summary` reports averages, hallucination rate and whether the sample is
  `pending`, `insufficient_sample` or `complete`.

The API does not create synthetic reviews and does not promote an AI result to ground truth. A review is evidence from
one human reviewer, not a replacement for a larger inter-rater reliability study.

Công cụ tổng hợp:

    cd backend
    python -m evaluation.summarize path/to/reviews.jsonl

Công cụ sẽ trả về:

- số mẫu đã được review;
- điểm trung bình theo từng tiêu chí;
- tỷ lệ hallucination;
- trạng thái pending, insufficient_sample hoặc complete.

Chỉ trạng thái complete khi có tối thiểu 30 review hợp lệ. Không được tự tạo review hoặc điền điểm giả để đạt ngưỡng.

## Quy trình đánh giá đề xuất

1. Chạy cùng một provider và model đã ghi trong báo cáo.
2. Lưu prompt version, model, timestamp và latency.
3. Chạy 30 case trong manifest.
4. Lưu raw output ở nơi không commit secret hoặc dữ liệu cá nhân.
5. Reviewer chấm kết quả mà không chỉnh sửa output gốc.
6. Ghi lại các failure case.
7. Tính kết quả bằng công cụ tổng hợp.
8. So sánh với baseline đơn giản hoặc đánh giá của giáo viên.
9. Trình bày giới hạn, không chỉ trình bày điểm trung bình.

## Nguyên tắc bảo vệ học thuật

- Mock AI dùng cho test deterministic, không phải bằng chứng AI có chất lượng.
- JSON hợp lệ không đồng nghĩa với feedback đúng.
- Speaking hiện chỉ đánh giá transcript về relevance, grammar và vocabulary.
- Không dùng kết quả AI để tuyên bố điểm IELTS hoặc điểm phát âm chính thức.
- Nếu không có reviewer thật, báo cáo phải ghi rõ AI evaluation đang ở trạng thái chưa hoàn tất.
