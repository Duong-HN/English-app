# Plan: chuyển phần học video sang YouTube Embed

## 1. Kết luận đề xuất

Chuyển từ việc tự lưu file video sang dùng YouTube Embed là hướng phù hợp cho MVP/demo:

- Không phải lưu binary, transcode hoặc trả bandwidth video từ backend.
- Có thể dùng nội dung từ các kênh chính thống.
- Giữ được metadata bài học, mapping vào lesson và tiến độ học của LearnMate.

Phương án được đề xuất là:

```text
Channel ID được duyệt
        -> đồng bộ uploads playlist
        -> lấy metadata video
        -> lưu catalog tạm thời
        -> admin duyệt và gắn vào lesson
        -> mobile phát bằng YouTube Embed
```

Không tự động hiển thị toàn bộ video vừa đồng bộ. Video phải qua bước duyệt/gắn bài học để tránh nội dung ngoài chủ đề và kiểm soát chất lượng giáo trình.

## 2. Phạm vi

### Làm trong giai đoạn này

- Hỗ trợ các channel YouTube được cấu hình sẵn bằng `channel_id`.
- Lấy uploads playlist của từng channel.
- Đồng bộ video mới/cập nhật vào database.
- Lọc video không public hoặc không cho phép embed.
- Cho admin xem danh sách video chờ duyệt.
- Gắn một video YouTube vào một lesson cụ thể.
- Phát video bằng YouTube Embed trong mobile.
- Lưu vị trí xem, trạng thái hoàn thành và lần đồng bộ gần nhất.
- Giữ transcript nội bộ nếu admin có nội dung được phép sử dụng.

### Chưa làm trong giai đoạn này

- Tải video hoặc audio từ YouTube về server.
- Cache bản sao audiovisual content.
- Tự động tải transcript/caption của kênh bên thứ ba.
- Tự động dùng AI để phân loại và publish video không qua admin.
- Cho learner nhập URL YouTube tùy ý.
- Đồng bộ view count, like count hoặc xây dựng ranking từ các số liệu đó.

## 3. Điều kiện cần chốt trước khi triển khai

- Xác nhận các channel ID chính xác; không nhận diện channel chỉ bằng tên hiển thị.
- Xác nhận quyền sử dụng nội dung, transcript/caption và việc gom dữ liệu của các channel khác content owner.
- Xác định rõ “whitelist” là allowlist nội bộ của LearnMate hay quyền/ủy quyền được YouTube/content owner công nhận. Hai khái niệm này không tương đương.
- Nếu chưa có quyền hoặc chưa có kết luận compliance, không coi catalog API tự động của British Council + IDP + IELTS Official là đã được phép. Fallback an toàn hơn cho demo là lưu thủ công từng video ID đã chọn và chỉ embed player chính thức; đây là phương án giảm rủi ro, không phải kết luận pháp lý.
- Xác định retention policy cho API Data YouTube: refresh sớm hơn hạn 30 ngày, đặt `metadata_expires_at`, và không hiển thị metadata đã hết hạn nếu chưa refresh.
- Bổ sung thông báo rằng app sử dụng YouTube API/YouTube Embed và cập nhật Privacy Policy nếu cần.

### 3.1. Kết quả kiểm tra policy hiện hành

Điểm cần sửa so với cách diễn giải trước: policy không chỉ nói về dữ liệu lấy bằng OAuth. Trong mục “Data Aggregation”, YouTube ghi rằng không được aggregate `API Data`, ngoại lệ hẹp là các channel thuộc cùng content owner được YouTube công nhận theo thỏa thuận cấp phép, và dữ liệu aggregate đó chỉ được hiển thị cho content owner tương ứng. Policy cũng nói các content owner khác nhau có thể được aggregate riêng theo từng owner nếu đã ủy quyền, nhưng không được combine dữ liệu giữa các owner.

Vì vậy, public video, channel chính thống hoặc allowlist nội bộ không tự động làm cho việc sync và hiển thị một catalog kết hợp nhiều owner trở thành compliant. Với ba channel khác owner, cần một trong các hướng sau:

1. Có quyền/ủy quyền và xác nhận use case phù hợp từ YouTube/content owner.
2. Xin API Compliance Audit hoặc hướng dẫn chính thức cho use case trước khi xây catalog aggregate.
3. Không dùng Data API để tạo catalog chung; admin khai báo thủ công từng video ID vào từng lesson, giữ attribution của YouTube và chỉ dùng official embed.

Đây là diễn giải kỹ thuật dựa trên [YouTube API Services Developer Policies](https://developers.google.com/youtube/terms/developer-policies), không thay thế tư vấn pháp lý hoặc quyết định compliance của YouTube.

## 4. Kiến trúc dữ liệu đề xuất

### 4.1. `youtube_channels`

Lưu cấu hình channel được phép đồng bộ:

```text
id
channel_id                  unique
display_name
owner_label                 ví dụ: British Council / IDP
uploads_playlist_id
permission_status           pending / verified / restricted
is_enabled
last_synced_at
created_at
updated_at
```

`uploads_playlist_id` lấy từ `channels.list(part=contentDetails)` và cache lại để không phải suy luận bằng tên channel ở mỗi lần sync.

### 4.2. `youtube_video_records`

Đây là catalog video lấy từ YouTube, tách khỏi lesson:

```text
id
youtube_video_id            unique
channel_id                  foreign key -> youtube_channels
playlist_id
source_title
source_description          chỉ lưu nếu retention policy cho phép
thumbnail_url
published_at
duration_seconds
caption_available
privacy_status
embeddable
made_for_kids
canonical_watch_url
metadata_synced_at
metadata_expires_at
last_seen_at
last_sync_error
unavailable_reason
consecutive_misses
sync_status                 discovered / approved / stale / restricted / unavailable / removed / integration_error
created_at
updated_at
```

Các field lấy từ YouTube như title, description, thumbnail, duration, published time, caption flag, privacy, region và embeddable là volatile API Data. Chỉ lưu phần tối thiểu cần cho UI, luôn gắn `metadata_synced_at`/`metadata_expires_at`, và refresh hoặc xóa trong tối đa 30 calendar days. Mapping do LearnMate tự tạo như `lesson_id`, skill, level, objective, sort order và ghi chú biên tập cần tách khỏi source metadata để không bị coi là metadata YouTube stale.

Không lưu `embed_html` từ API. Luôn validate `youtube_video_id` rồi tự tạo URL embed ở backend.

### 4.3. Mở rộng `lesson_media`

Giữ model `LessonMedia` hiện tại để không phá vỡ local media, bổ sung:

```text
provider                    local / youtube
youtube_video_record_id     nullable
youtube_video_id            nullable, index
```

Các field `storage_key`, `file_size_bytes` chỉ dùng cho `provider=local`. Các field `source_url`, duration và transcript cần được xử lý khác nhau theo provider.

Có thể giữ local provider làm fallback cho video do nhóm tự quay/sở hữu. Không cần xóa ngay pipeline upload hiện tại.

## 5. Backend flow

### 5.1. Đồng bộ channel

Backend chạy bằng API key server-side, không đưa key vào Flutter:

1. Đọc danh sách channel đã enable.
2. Gọi `channels.list(part=contentDetails&id=...)` nếu chưa có uploads playlist.
3. Gọi `playlistItems.list(part=snippet,contentDetails,status&playlistId=...)`.
4. Xử lý `nextPageToken`, giới hạn page size hợp lý.
5. Gom video IDs rồi gọi `videos.list` theo batch để lấy `snippet`, `contentDetails`, `status`.
6. Upsert theo `youtube_video_id`.
7. Ghi `metadata_synced_at`, `metadata_expires_at`, `last_seen_at` và xóa `last_sync_error` khi sync thành công.
8. Chỉ đánh dấu `removed` sau một lần full scan có phạm vi xác định hoặc một response xác nhận video đã bị xóa; không kết luận removed từ lỗi quota, timeout, 5xx hoặc một incremental scan chưa đầy đủ.

Không dùng `search.list` cho luồng chính vì uploads playlist đã xác định rõ nguồn và tiết kiệm quota hơn.

### 5.2. Lọc trước khi đưa vào admin queue

Chỉ đưa vào danh sách candidate nếu:

- `privacyStatus=public`.
- `status.embeddable=true`.
- `contentDetails.regionRestriction` không chặn vùng triển khai của app. Với `YOUTUBE_CONTENT_REGION=VN`: nếu có `allowed`, `VN` phải nằm trong danh sách; nếu có `blocked`, `VN` không được nằm trong danh sách. Không có object này nghĩa là API không trả restriction cho video đó, không phải cam kết tuyệt đối rằng mọi region đều xem được.
- Channel đúng với allowlist.
- Không phải live/upcoming nếu lesson yêu cầu video học cố định.

Thông tin `status.madeForKids` phải được kiểm tra trước khi embed. `status.selfDeclaredMadeForKids` chỉ có thể trả về trong request được channel owner ủy quyền, nên không dùng field đó làm điều kiện duy nhất với public API key. Với MVP IELTS, video có `madeForKids=true` chuyển sang `restricted` và không publish cho tới khi có cấu hình privacy/tracking phù hợp; không tự động coi nó là video bình thường.

`status.embeddable=false` là điều kiện loại trực tiếp. Ngoài pre-check bằng API, player runtime vẫn là nguồn kiểm tra cuối vì region, privacy hoặc Referer có thể làm embed lỗi sau đó.

### 5.3. Quy tắc trạng thái khi sync

| Trạng thái | Ý nghĩa | Hành động |
|---|---|---|
| `discovered` | Video mới, chưa được admin duyệt | Không hiển thị cho learner |
| `approved` | Đã được admin gắn vào lesson | Có thể publish nếu metadata còn hạn và playable |
| `stale` | Sync thất bại tạm thời hoặc metadata quá hạn | Giữ mapping, cảnh báo admin, không dùng dữ liệu YouTube stale để render mới |
| `restricted` | Region blocked, made-for-kids chưa có policy, private hoặc không embeddable | Ẩn khỏi learner, giữ lý do |
| `unavailable` | API/player xác nhận không phát được | Ẩn khỏi learner, cho phép admin re-check/re-attach |
| `removed` | Full scan hoặc API xác nhận video đã bị xóa | Giữ audit/progress, ngừng publish |
| `integration_error` | Lỗi app như thiếu Referer, WebView bridge hoặc player config | Không gán lỗi cho video; sửa integration rồi retry |

Các lỗi quota, timeout, network, 5xx và lỗi xác thực tạm thời chỉ ghi `last_sync_error`/`stale`, không đánh dấu `removed`. Runtime error `100` (not found/private) và `101`/`150` (owner không cho embed) có thể chuyển sang `unavailable`; error `153` (thiếu Referer/API client identification) phải chuyển sang `integration_error`.

### 5.4. API nội bộ đề xuất

```text
GET  /api/v1/content/admin/youtube/channels
POST /api/v1/content/admin/youtube/channels
POST /api/v1/content/admin/youtube/sync
GET  /api/v1/content/admin/youtube/videos?status=discovered
POST /api/v1/content/admin/youtube/videos/{id}/attach
POST /api/v1/content/admin/youtube/videos/{id}/hide
POST /api/v1/content/admin/youtube/sync/{channel_id}
```

`attach` nhận:

```json
{
  "lesson_id": "...",
  "display_title": "...",
  "sort_order": 0,
  "transcript": "...",
  "is_published": false
}
```

Mặc định `is_published=false`; admin phải publish sau khi kiểm tra nội dung.

### 5.5. Cơ chế chạy sync

Giai đoạn đầu không cần thêm hệ thống queue phức tạp:

- Có nút `Sync now` trong admin.
- Có CLI/script để cron gọi mỗi ngày hoặc mỗi tuần.
- Sync chạy ở backend, có log số request, số candidate, số record update và lỗi.
- Không sync khi learner mở màn hình curriculum.

Sau này nếu số channel tăng mới cân nhắc Celery/worker riêng.

## 6. Admin dashboard

Thêm màn hình `YouTube sources`:

### Channel management

- Thêm channel bằng `channel_id`.
- Hiển thị tên thật trả về từ API để admin đối chiếu.
- Bật/tắt sync.
- Hiển thị owner label và permission status.
- Nút sync từng channel hoặc toàn bộ.

### Video review queue

Mỗi candidate hiển thị:

- Thumbnail từ YouTube.
- Title, channel, ngày publish, duration.
- Caption available.
- Embeddable/privacy status.
- Link mở video gốc trên YouTube.
- Trạng thái: chưa gắn, đã gắn, ẩn, unavailable.

### Attach to lesson

- Chọn course/unit/lesson.
- Gán skill: listening, speaking, vocabulary...
- Gán level/topic do LearnMate quản lý.
- Nhập transcript riêng nếu được phép sử dụng.
- Preview embed.
- Publish/unpublish.

Các tag level, skill, objective và thứ tự bài là dữ liệu do LearnMate sở hữu; không suy ra ranking hoặc metric từ view/like của YouTube.

## 7. Mobile player

### Phân nhánh player

```text
LessonMedia.provider == local
    -> VideoPlayerController hiện tại

LessonMedia.provider == youtube
    -> YouTube IFrame/Embed player
```

Không dùng `VideoPlayerController.networkUrl` với URL `youtube.com/embed/...`; đó là HTML embed URL, không phải raw video stream.

### Hành vi cần giữ

- Play/pause.
- Fullscreen/landscape nếu nền tảng cho phép.
- Seek.
- Resume từ vị trí đã lưu.
- Gửi progress về `/media-progress` định kỳ và khi pause/background/dispose.
- Đánh dấu hoàn thành khi learner xem đủ ngưỡng thống nhất, ví dụ 80%.
- Hiển thị transcript nội bộ bên dưới player nếu có.
- Hiển thị nút/link mở video gốc trên YouTube.

### Tích hợp Flutter

Player cần hỗ trợ IFrame JavaScript API hoặc WebView bridge để nhận:

- `onReady`.
- `onStateChange`.
- `currentTime`.
- `duration`.
- `onError`.

Trên mobile WebView phải cấu hình `Referer/app ID` phù hợp với yêu cầu của YouTube; không gửi API key hoặc JWT LearnMate vào YouTube iframe.

### Caption

`videos.list` chỉ cho biết caption có tồn tại qua `contentDetails.caption`, không trả luôn nội dung transcript. `captions.list` yêu cầu OAuth 2.0; `captions.download` còn yêu cầu user có quyền edit video và có quota cost riêng. Vì vậy public API key của LearnMate không đủ để tải caption của British Council/IDP/IELTS Official.

Giai đoạn đầu chỉ:

- Hiển thị caption native của YouTube nếu video có caption.
- Hiển thị transcript LearnMate nếu admin có nội dung được phép sử dụng.
- Không tự tải, scrape hoặc đưa caption của channel bên thứ ba vào database/LLM.

## 8. Progress và AI grounding

### Progress

Tiếp tục dùng `LessonProgress.media_progress` hiện tại, key theo `LessonMedia.id`:

```json
{
  "media-id": {
    "position_seconds": 42,
    "completed": false,
    "updated_at": "..."
  }
}
```

### Cơ chế lưu với YouTube IFrame Player

- Khi `onReady` và duration đã khác `0`, gọi `seekTo` theo `position_seconds` đã lưu; `getDuration()` có thể trả `0` trước khi metadata được load.
- Khi player ở trạng thái `PLAYING`, poll `getCurrentTime()` mỗi 10–15 giây, debounce và gửi vị trí mới nhất về `/media-progress`; không gọi API mỗi frame hoặc mỗi giây.
- Lưu ngay khi `PAUSED`, `ENDED`, app chuyển background và khi WebView/player bị dispose.
- `ENDED` đặt `completed=true`. MVP có thể giữ ngưỡng 80% như local player, nhưng nên ghi rõ đây là ngưỡng tiến độ nội bộ và không trao thưởng cho việc xem, like hoặc subscribe YouTube.
- Khi resume, nếu video đã đổi ID hoặc metadata không còn hợp lệ thì không seek mù; reload player và báo trạng thái cho learner.
- Backend giữ last-write-wins theo `updated_at`, validate `media_id` thuộc lesson và không nhận progress cho record `removed/restricted`.

Nếu video bị remove/unavailable, giữ progress lịch sử nhưng không cho player tiếp tục phát. Lỗi `153` do thiếu Referer không được mất progress và không được đánh dấu video removed.

### AI

- AI chỉ dùng transcript nếu transcript đó do LearnMate sở hữu hoặc có quyền sử dụng.
- Nếu không có transcript, AI dùng lesson objective/body và metadata tối thiểu, không tự scrape nội dung YouTube.
- `transcript` phải có provenance/license/permission record: do LearnMate tự viết, do content owner cung cấp, hoặc có giấy phép sử dụng rõ ràng.
- Không gửi toàn bộ description/caption của video bên thứ ba vào AI nếu chưa xác định quyền sử dụng. Nếu chỉ có caption native trong player, coi đó là dữ liệu để learner xem trong YouTube, không tự động biến thành AI context.

## 9. Migration plan

### Phase 0 — quyết định nguồn và compliance

- [ ] Xác nhận channel IDs chính thức.
- [ ] Xác nhận quyền/điều kiện sử dụng nội dung.
- [ ] Xác định use case có rơi vào Data Aggregation; không triển khai catalog combine nhiều owner nếu chưa có permission/compliance decision.
- [ ] Nếu chưa được phép aggregate, chọn fallback manual từng video ID, không dùng Data API để tạo feed chung.
- [ ] Tạo Google Cloud project riêng cho production.
- [ ] Bật YouTube Data API v3 và tạo API key giới hạn theo API.

### Phase 1 — model và backend sync

- [ ] Tạo migration cho `youtube_channels`.
- [ ] Tạo migration cho `youtube_video_records`.
- [ ] Mở rộng `lesson_media` với provider YouTube.
- [ ] Implement client YouTube ở backend.
- [ ] Implement pagination, batching, upsert và retention 30 ngày.
- [ ] Viết test cho duplicate, pagination, expiry, region restriction, madeForKids, unavailable, removed và embeddable filter.

### Phase 2 — admin review

- [ ] Thêm cấu hình channel.
- [ ] Thêm nút sync.
- [ ] Thêm candidate queue.
- [ ] Thêm attach/publish/unpublish.
- [ ] Thêm preview embed.
- [ ] Ghi audit log cho sync, attach, publish và hide.

### Phase 3 — mobile embed

- [ ] Thêm provider branch.
- [ ] Tích hợp YouTube IFrame/WebView.
- [ ] Thiết lập Referer/app ID.
- [ ] Implement ready/state/currentTime callbacks.
- [ ] Poll `getCurrentTime()` theo chu kỳ và debounce progress updates.
- [ ] Kết nối resume/progress/completion.
- [ ] Test Android, iOS và web preview nếu còn hỗ trợ.

### Phase 4 — migration nội dung demo

- [ ] Giữ 3 video lesson hiện tại trong `english_a2_b1.json` làm lesson target.
- [ ] Admin sync các channel.
- [ ] Chọn video phù hợp và attach vào 3 lesson.
- [ ] Review title, duration, caption và embeddable status.
- [ ] Publish sau khi kiểm tra trên thiết bị thật.

### Phase 5 — vận hành

- [ ] Chạy sync định kỳ hằng tuần.
- [ ] Cảnh báo video bị xóa, private, region restricted, madeForKids chưa được xử lý hoặc không embeddable.
- [ ] Xóa/refresh metadata quá hạn; không dùng stale metadata sau `metadata_expires_at`.
- [ ] Theo dõi quota và lỗi YouTube API.
- [ ] Cập nhật Privacy Policy và trang thông tin nguồn.

## 10. Acceptance criteria

- Admin cấu hình được channel bằng ID và chỉ channel enabled mới được sync.
- Sync lấy được uploads playlist, xử lý pagination và không tạo duplicate.
- Chỉ video public + embeddable mới có thể đưa vào queue/publish.
- Learner chỉ thấy video đã được admin attach và publish.
- Mobile phát bằng YouTube Embed, không tải video về backend.
- Resume/progress/completion hoạt động tương đương local media hiện tại.
- API key chỉ tồn tại ở backend.
- Video bị xóa/private/region-restricted/madeForKids chưa compliant/unembeddable được ẩn với reason rõ ràng.
- Lỗi sync tạm thời chỉ thành `stale`, không xóa nhầm video.
- Metadata có `last_synced_at`, `metadata_expires_at` và được refresh hoặc xóa trong giới hạn retention.
- Progress được lưu theo IFrame events + polling `getCurrentTime()`, không gửi API mỗi frame.
- Transcript có provenance/license; không có caption third-party nào được tự động tải vào AI context.
- UI giữ YouTube attribution, player controls, links và quảng cáo; không reward learner cho view/like/subscribe.
- Test backend, Flutter và admin build đều pass.

## 11. Rủi ro và phương án giảm thiểu

| Rủi ro | Mức độ | Giảm thiểu |
|---|---:|---|
| Video bị xóa, private, region blocked hoặc tắt embed | Cao | Pre-check API, runtime error mapping, trạng thái unavailable/restricted và re-sync |
| Vi phạm điều kiện aggregate nhiều channel | Cao | Không combine API Data giữa các owner nếu chưa có permission/compliance decision; fallback manual video ID |
| YouTube API hết quota | Trung bình | Không dùng `search.list`, sync incremental, cache playlist ID |
| WebView không phát do thiếu Referer | Trung bình | Cấu hình app ID/Referer và test Android/iOS thật |
| Không có quyền lấy caption/transcript | Cao | Chỉ hiển thị native caption; transcript AI phải có provenance/license |
| Metadata quá hạn hoặc stale | Cao | `metadata_expires_at`, refresh trước 30 ngày, không render stale source fields |
| YouTube thay đổi player/policy | Trung bình | Dùng official IFrame/WebView, không scrape/direct-stream |
| Learner mất mạng | Trung bình | Hiển thị trạng thái rõ ràng; không cam kết offline playback |

## 12. Tài liệu tham khảo chính thức

- [YouTube Data API — Channels](https://developers.google.com/youtube/v3/docs/channels)
- [YouTube Data API — PlaylistItems](https://developers.google.com/youtube/v3/docs/playlistItems/list)
- [YouTube Data API — Videos](https://developers.google.com/youtube/v3/docs/videos)
- [YouTube Embedded Players and Player Parameters](https://developers.google.com/youtube/player_parameters)
- [YouTube API Services — Required Minimum Functionality](https://developers.google.com/youtube/terms/required-minimum-functionality)
- [YouTube API Services — Developer Policies](https://developers.google.com/youtube/terms/developer-policies)
- [YouTube API — Captions implementation](https://developers.google.com/youtube/v3/guides/implementation/captions)
- [YouTube IFrame Player API reference](https://developers.google.com/youtube/iframe_api_reference)
- [YouTube Data API — Quota and Getting Started](https://developers.google.com/youtube/v3/getting-started)

## Quyết định cần review

1. Có permission/compliance approval rõ ràng để aggregate API Data từ cả ba content owner hay không?
2. Nếu chưa có, có chuyển sang manual từng video ID, không sync feed chung, không?
3. Có giữ local media provider làm fallback không?
4. Video madeForKids sẽ bị loại khỏi MVP hay sẽ triển khai privacy/tracking mode riêng?
5. Ngưỡng hoàn thành video là 80% hay cần yêu cầu xem đến cuối?
6. Transcript dùng cho AI sẽ do ai cung cấp và được cấp phép theo cách nào?
