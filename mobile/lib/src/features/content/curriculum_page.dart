import 'dart:async';

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'package:video_player/video_player.dart';

import '../../core/api_client.dart';

class CurriculumPage extends StatefulWidget {
  const CurriculumPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<CurriculumPage> createState() => _CurriculumPageState();
}

class _CurriculumPageState extends State<CurriculumPage> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.courses();
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.courses();
    setState(() => _future = next);
    await next;
  }

  Future<void> _openLesson(Map<String, dynamic> lesson) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            LessonPage(apiClient: widget.apiClient, lessonSummary: lesson),
      ),
    );
    if (mounted) _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Thư viện giáo trình')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Map<String, dynamic>>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return ListView(
                padding: const EdgeInsets.all(24),
                children: [
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.cloud_off_outlined),
                      title: Text(_errorText(snapshot.error)),
                      trailing: TextButton(
                        onPressed: _refresh,
                        child: const Text('Thử lại'),
                      ),
                    ),
                  ),
                ],
              );
            }
            final courses = snapshot.data ?? const [];
            if (courses.isEmpty) {
              return ListView(
                padding: const EdgeInsets.all(24),
                children: const [
                  Card(
                    child: ListTile(
                      leading: Icon(Icons.menu_book_outlined),
                      title: Text('Chưa có khóa học'),
                    ),
                  ),
                ],
              );
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              children: [
                Text(
                  'Học theo chương',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 6),
                const Text(
                  'Mỗi không gian tự học có tiến độ riêng. Chọn khóa theo level hoặc khóa IELTS theo band mục tiêu.',
                ),
                const SizedBox(height: 18),
                ...courses.map(
                  (course) =>
                      _CourseCard(course: course, onOpenLesson: _openLesson),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CourseCard extends StatelessWidget {
  const _CourseCard({required this.course, required this.onOpenLesson});

  final Map<String, dynamic> course;
  final ValueChanged<Map<String, dynamic>> onOpenLesson;

  @override
  Widget build(BuildContext context) {
    final kind = course['kind']?.toString();
    final level = course['level']?.toString();
    final bandMin = course['band_min']?.toString();
    final bandMax = course['band_max']?.toString();
    final units = _asMaps(course['units']);
    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  child: Icon(
                    kind == 'ielts'
                        ? Icons.workspace_premium_outlined
                        : Icons.auto_stories_outlined,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        course['title']?.toString() ?? 'Khóa học',
                        style: Theme.of(context).textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 4),
                      Text(course['description']?.toString() ?? ''),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              children: [
                if (level != null) Chip(label: Text('Level $level')),
                if (bandMin != null && bandMax != null)
                  Chip(label: Text('IELTS $bandMin-$bandMax')),
              ],
            ),
            ...units.map((unit) {
              final lessons = _asMaps(unit['lessons']);
              return ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text(
                  'Chương ${unit['unit_number']}: ${unit['title'] ?? ''}',
                ),
                subtitle: Text(unit['objective']?.toString() ?? ''),
                children: lessons
                    .map(
                      (lesson) => ListTile(
                        contentPadding: const EdgeInsets.only(left: 12),
                        leading: Icon(
                          lesson['progress_status']?.toString() == 'completed'
                              ? Icons.check_circle
                              : _skillIcon(lesson['skill']?.toString()),
                          color:
                              lesson['progress_status']?.toString() ==
                                  'completed'
                              ? Colors.green
                              : null,
                        ),
                        title: Text(
                          'Bài ${lesson['lesson_number']}: ${lesson['title'] ?? ''}',
                        ),
                        subtitle: Text(_lessonSummaryText(lesson)),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => onOpenLesson({
                          ...lesson,
                          'course_code': course['code'],
                        }),
                      ),
                    )
                    .toList(),
              );
            }),
          ],
        ),
      ),
    );
  }
}

class LessonPage extends StatefulWidget {
  const LessonPage({
    super.key,
    required this.apiClient,
    required this.lessonSummary,
  });

  final ApiClient apiClient;
  final Map<String, dynamic> lessonSummary;

  @override
  State<LessonPage> createState() => _LessonPageState();
}

class _LessonPageState extends State<LessonPage> {
  late Future<Map<String, dynamic>> _future;
  late final TextEditingController _answerController;
  bool _saving = false;
  bool _analyzing = false;
  Map<String, dynamic>? _analysis;
  String? _error;

  String get _lessonId => widget.lessonSummary['id']?.toString() ?? '';

  @override
  void initState() {
    super.initState();
    _answerController = TextEditingController();
    _future = widget.apiClient.lesson(_lessonId);
  }

  @override
  void dispose() {
    _answerController.dispose();
    super.dispose();
  }

  Future<void> _analyzeLesson(Map<String, dynamic> lesson) async {
    final inputText = _answerController.text.trim();
    if (inputText.length < 3) {
      setState(
        () => _error = 'Hãy nhập ít nhất một câu trả lời trước khi gửi AI.',
      );
      return;
    }
    setState(() {
      _analyzing = true;
      _error = null;
    });
    final type = switch (lesson['skill']?.toString()) {
      'writing' => 'writing',
      'speaking' => 'speaking',
      _ => 'reading',
    };
    try {
      final response = await widget.apiClient.analyze(
        type: type,
        inputText: inputText,
        lessonId: _lessonId,
      );
      if (mounted) setState(() => _analysis = response);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể nhận phản hồi từ AI.');
    } finally {
      if (mounted) setState(() => _analyzing = false);
    }
  }

  Future<void> _complete() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final lesson = await widget.apiClient.updateLessonProgress(
        lessonId: _lessonId,
        status: 'completed',
      );
      if (!mounted) return;
      setState(() => _future = Future.value(lesson));
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã hoàn thành bài học.')));
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể lưu tiến độ bài học.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Bài học')),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text(_errorText(snapshot.error)));
          }
          final lesson = snapshot.data ?? widget.lessonSummary;
          final media = List<Map<String, dynamic>>.from(
            _asMaps(lesson['media']),
          );
          final legacyUrl = lesson['media_url']?.toString();
          if (media.isEmpty && legacyUrl != null && legacyUrl.isNotEmpty) {
            media.add({
              'id': 'legacy-media',
              'media_type': lesson['content_type']?.toString() == 'video'
                  ? 'video'
                  : 'audio',
              'title': 'Media bài học',
              'media_url': legacyUrl,
              'mime_type': lesson['content_type']?.toString() == 'video'
                  ? 'video/mp4'
                  : 'audio/mpeg',
              'transcript': lesson['transcript'],
            });
          }
          final progress = lesson['media_progress'] is Map
              ? (lesson['media_progress'] as Map).map(
                  (key, value) => MapEntry(key.toString(), value),
                )
              : <String, dynamic>{};
          final transcript = lesson['transcript']?.toString();
          final completed =
              lesson['progress_status']?.toString() == 'completed';
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
            children: [
              Text(
                lesson['title']?.toString() ?? 'Bài học',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(lesson['summary']?.toString() ?? ''),
              const SizedBox(height: 16),
              if (media.isEmpty)
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.library_music_outlined),
                    title: Text('Media đang được bổ sung'),
                    subtitle: Text(
                      'Bài học đã có nội dung; admin có thể gắn audio/video từ thư viện media.',
                    ),
                  ),
                )
              else
                ...media.map(
                  (item) => _LessonMediaCard(
                    key: ValueKey(item['id']),
                    apiClient: widget.apiClient,
                    lessonId: _lessonId,
                    media: item,
                    initialPositionSeconds: _mediaPosition(
                      progress[item['id']?.toString()],
                    ),
                  ),
                ),
              const SizedBox(height: 14),
              Text('Nội dung', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(lesson['body']?.toString() ?? ''),
                ),
              ),
              if (transcript != null && transcript.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(
                  'Transcript bài học',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: SelectableText(transcript),
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Trợ lý AI theo bài học',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'Nhập câu trả lời hoặc tóm tắt của bạn. AI sẽ dùng mục tiêu, nội dung và transcript của bài này để phản hồi.',
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        key: const Key('lesson-ai-input'),
                        controller: _answerController,
                        minLines: 3,
                        maxLines: 6,
                        decoration: const InputDecoration(
                          hintText: 'Viết câu trả lời bằng tiếng Anh…',
                          border: OutlineInputBorder(),
                        ),
                      ),
                      const SizedBox(height: 10),
                      FilledButton.icon(
                        key: const Key('lesson-ai-analyze'),
                        onPressed: _analyzing
                            ? null
                            : () => _analyzeLesson(lesson),
                        icon: _analyzing
                            ? const SizedBox.square(
                                dimension: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.auto_awesome_outlined),
                        label: Text(
                          _analyzing ? 'Đang phân tích…' : 'Nhờ AI nhận xét',
                        ),
                      ),
                      if (_analysis?['result'] is Map) ...[
                        const SizedBox(height: 14),
                        Builder(
                          builder: (context) {
                            final result = (_analysis!['result'] as Map).map(
                              (key, value) => MapEntry(key.toString(), value),
                            );
                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Divider(),
                                Text(
                                  result['summary']?.toString() ??
                                      'Đã nhận phản hồi từ AI.',
                                  key: const Key('lesson-ai-summary'),
                                ),
                                if (result['score'] != null)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 6),
                                    child: Text(
                                      'Điểm formative: ${result['score']}/10',
                                    ),
                                  ),
                              ],
                            );
                          },
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 10),
                Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 18),
              FilledButton.icon(
                key: const Key('lesson-complete'),
                onPressed: _saving || completed ? null : _complete,
                icon: _saving
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.check_circle_outline),
                label: Text(
                  completed ? 'Đã hoàn thành' : 'Đánh dấu hoàn thành',
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _LessonMediaCard extends StatelessWidget {
  const _LessonMediaCard({
    super.key,
    required this.apiClient,
    required this.lessonId,
    required this.media,
    required this.initialPositionSeconds,
  });

  final ApiClient apiClient;
  final String lessonId;
  final Map<String, dynamic> media;
  final int initialPositionSeconds;

  @override
  Widget build(BuildContext context) {
    final isVideo = media['media_type']?.toString() == 'video';
    if (isVideo) {
      return _VideoMediaCard(
        apiClient: apiClient,
        lessonId: lessonId,
        media: media,
        initialPositionSeconds: initialPositionSeconds,
      );
    }
    return _AudioMediaCard(
      apiClient: apiClient,
      lessonId: lessonId,
      media: media,
      initialPositionSeconds: initialPositionSeconds,
    );
  }
}

class _AudioMediaCard extends StatefulWidget {
  const _AudioMediaCard({
    required this.apiClient,
    required this.lessonId,
    required this.media,
    required this.initialPositionSeconds,
  });

  final ApiClient apiClient;
  final String lessonId;
  final Map<String, dynamic> media;
  final int initialPositionSeconds;

  @override
  State<_AudioMediaCard> createState() => _AudioMediaCardState();
}

class _AudioMediaCardState extends State<_AudioMediaCard> {
  late final AudioPlayer _player;
  Duration _position = Duration.zero;
  bool _loaded = false;
  bool _savedCompleted = false;
  bool _loading = false;
  String? _error;

  String get _mediaId => widget.media['id']?.toString() ?? '';

  @override
  void initState() {
    super.initState();
    _player = AudioPlayer();
    _position = Duration(seconds: widget.initialPositionSeconds);
    _player.positionStream.listen((position) {
      if (!mounted) return;
      setState(() => _position = position);
      final duration = _player.duration;
      if (!_savedCompleted &&
          duration != null &&
          duration.inSeconds > 0 &&
          position.inSeconds >= (duration.inSeconds * .8).round()) {
        _savedCompleted = true;
        _saveProgress(completed: true);
      }
    });
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _toggle() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (_player.playing) {
        await _player.pause();
        await _saveProgress();
      } else {
        if (!_loaded) {
          final url = widget.apiClient.resolveMediaUrl(
            widget.media['media_url']?.toString() ?? '',
          );
          await _player.setUrl(url, headers: widget.apiClient.mediaHeaders());
          if (widget.initialPositionSeconds > 0) {
            await _player.seek(
              Duration(seconds: widget.initialPositionSeconds),
            );
          }
          _loaded = true;
        }
        await _player.play();
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể phát audio của bài học.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _saveProgress({bool completed = false}) async {
    if (_mediaId.isEmpty) return;
    try {
      await widget.apiClient.updateLessonMediaProgress(
        lessonId: widget.lessonId,
        mediaId: _mediaId,
        positionSeconds: _position.inSeconds,
        completed: completed,
      );
    } catch (_) {
      // Playback should continue even when progress sync is temporarily offline.
    }
  }

  @override
  Widget build(BuildContext context) {
    final duration = _player.duration;
    final maxSeconds = duration?.inSeconds ?? 1;
    final currentSeconds = _position.inSeconds.clamp(0, maxSeconds);
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.headphones_outlined),
              title: Text(widget.media['title']?.toString() ?? 'Audio bài học'),
              subtitle: const Text('Audio bài học · tiến độ được lưu tự động'),
              trailing: IconButton(
                tooltip: _player.playing ? 'Tạm dừng' : 'Phát',
                onPressed: _loading ? null : _toggle,
                icon: _loading
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(_player.playing ? Icons.pause : Icons.play_arrow),
              ),
            ),
            Slider(
              value: currentSeconds.toDouble(),
              max: maxSeconds.toDouble(),
              onChanged: duration == null
                  ? null
                  : (value) {
                      _player.seek(Duration(seconds: value.round()));
                      setState(
                        () => _position = Duration(seconds: value.round()),
                      );
                    },
            ),
            if (widget.media['transcript']?.toString().isNotEmpty == true)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Transcript'),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SelectableText(
                      widget.media['transcript'].toString(),
                    ),
                  ),
                ],
              ),
            if (_error != null)
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
    );
  }
}

class _VideoMediaCard extends StatefulWidget {
  const _VideoMediaCard({
    required this.apiClient,
    required this.lessonId,
    required this.media,
    required this.initialPositionSeconds,
  });

  final ApiClient apiClient;
  final String lessonId;
  final Map<String, dynamic> media;
  final int initialPositionSeconds;

  @override
  State<_VideoMediaCard> createState() => _VideoMediaCardState();
}

class _VideoMediaCardState extends State<_VideoMediaCard> {
  VideoPlayerController? _controller;
  Future<void>? _initialization;
  bool _savedCompleted = false;
  String? _error;

  String get _mediaId => widget.media['id']?.toString() ?? '';

  Future<void> _start() async {
    try {
      if (_controller == null) {
        final url = widget.apiClient.resolveMediaUrl(
          widget.media['media_url']?.toString() ?? '',
        );
        final controller = VideoPlayerController.networkUrl(
          Uri.parse(url),
          httpHeaders: widget.apiClient.mediaHeaders(),
        );
        _controller = controller;
        _initialization = controller.initialize();
        await _initialization;
        if (widget.initialPositionSeconds > 0) {
          await controller.seekTo(
            Duration(seconds: widget.initialPositionSeconds),
          );
        }
        controller.addListener(_onVideoChanged);
      }
      await _controller!.play();
      if (mounted) setState(() => _error = null);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể phát video của bài học.');
    }
  }

  void _onVideoChanged() {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) return;
    final duration = controller.value.duration;
    final position = controller.value.position;
    if (!_savedCompleted &&
        duration.inSeconds > 0 &&
        position.inSeconds >= (duration.inSeconds * .8).round()) {
      _savedCompleted = true;
      _saveProgress(completed: true);
    }
    if (mounted) setState(() {});
  }

  Future<void> _saveProgress({bool completed = false}) async {
    final controller = _controller;
    if (_mediaId.isEmpty || controller == null) return;
    try {
      await widget.apiClient.updateLessonMediaProgress(
        lessonId: widget.lessonId,
        mediaId: _mediaId,
        positionSeconds: controller.value.position.inSeconds,
        completed: completed,
      );
    } catch (_) {
      // Playback should continue even when progress sync is temporarily offline.
    }
  }

  @override
  void dispose() {
    final controller = _controller;
    if (controller != null) {
      controller.removeListener(_onVideoChanged);
      unawaited(_saveProgress());
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    final initialized = controller != null && controller.value.isInitialized;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.ondemand_video_outlined),
              title: Text(widget.media['title']?.toString() ?? 'Video bài học'),
              subtitle: const Text('Video bài học · tiến độ được lưu tự động'),
              trailing: IconButton(
                tooltip: initialized && controller.value.isPlaying
                    ? 'Tạm dừng'
                    : 'Phát',
                onPressed: initialized
                    ? () {
                        if (controller.value.isPlaying) {
                          controller.pause();
                          _saveProgress();
                        } else {
                          controller.play();
                        }
                        setState(() {});
                      }
                    : _start,
                icon: Icon(
                  initialized && controller.value.isPlaying
                      ? Icons.pause
                      : Icons.play_arrow,
                ),
              ),
            ),
            if (_initialization != null && !initialized)
              FutureBuilder<void>(
                future: _initialization,
                builder: (context, snapshot) => snapshot.hasError
                    ? Text(
                        'Không thể tải video.',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      )
                    : const Padding(
                        padding: EdgeInsets.all(12),
                        child: Center(child: CircularProgressIndicator()),
                      ),
              )
            else if (initialized) ...[
              AspectRatio(
                aspectRatio: controller.value.aspectRatio == 0
                    ? 16 / 9
                    : controller.value.aspectRatio,
                child: VideoPlayer(controller),
              ),
              VideoProgressIndicator(controller, allowScrubbing: true),
            ],
            if (widget.media['transcript']?.toString().isNotEmpty == true)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: const Text('Transcript / caption'),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SelectableText(
                      widget.media['transcript'].toString(),
                    ),
                  ),
                ],
              ),
            if (_error != null)
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
    );
  }
}

int _mediaPosition(Object? value) {
  if (value is! Map) return 0;
  final raw = value['position_seconds'];
  if (raw is num) return raw.round().clamp(0, 86400);
  return int.tryParse(raw?.toString() ?? '')?.clamp(0, 86400) ?? 0;
}

List<Map<String, dynamic>> _asMaps(Object? value) {
  if (value is! List) return const [];
  return value.whereType<Map>().map((item) {
    return item.map((key, value) => MapEntry(key.toString(), value));
  }).toList();
}

IconData _skillIcon(String? skill) => switch (skill?.toLowerCase()) {
  'reading' => Icons.menu_book_outlined,
  'listening' => Icons.headphones_outlined,
  'speaking' => Icons.record_voice_over_outlined,
  'writing' => Icons.edit_note_outlined,
  'grammar' => Icons.rule_outlined,
  _ => Icons.auto_stories_outlined,
};

String _errorText(Object? error) {
  if (error is ApiException) return error.message;
  return 'Không thể tải nội dung giáo trình.';
}

String _lessonSummaryText(Map<String, dynamic> lesson) {
  final mediaCount = lesson['media_count'] is num
      ? (lesson['media_count'] as num).toInt()
      : 0;
  final mediaLabel = mediaCount > 0 ? ' · $mediaCount media' : '';
  return '${lesson['content_type'] ?? lesson['skill'] ?? ''} · '
      '${lesson['duration_minutes'] ?? 0} phút$mediaLabel';
}
