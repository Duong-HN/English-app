import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

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
                        subtitle: Text(
                          '${lesson['content_type'] ?? lesson['skill'] ?? ''} · ${lesson['duration_minutes'] ?? 0} phút',
                        ),
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
  AudioPlayer? _audioPlayer;
  bool _playing = false;
  bool _saving = false;
  String? _error;

  String get _lessonId => widget.lessonSummary['id']?.toString() ?? '';

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.lesson(_lessonId);
  }

  @override
  void dispose() {
    _audioPlayer?.dispose();
    super.dispose();
  }

  Future<void> _toggleAudio(String url) async {
    try {
      _audioPlayer ??= AudioPlayer();
      if (_playing) {
        await _audioPlayer!.pause();
      } else {
        await _audioPlayer!.setUrl(url);
        await _audioPlayer!.play();
      }
      if (mounted) setState(() => _playing = !_playing);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể phát audio của bài học.');
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
          final mediaUrl = lesson['media_url']?.toString();
          final transcript = lesson['transcript']?.toString();
          final isVideo = lesson['content_type']?.toString() == 'video';
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
              if (mediaUrl != null && mediaUrl.isNotEmpty)
                Card(
                  child: ListTile(
                    leading: Icon(
                      isVideo
                          ? Icons.ondemand_video_outlined
                          : Icons.headphones_outlined,
                    ),
                    title: Text(isVideo ? 'Video bài học' : 'Audio bài học'),
                    subtitle: Text(mediaUrl),
                    trailing: IconButton(
                      tooltip: _playing ? 'Tạm dừng' : 'Phát',
                      onPressed: () => _toggleAudio(mediaUrl),
                      icon: Icon(_playing ? Icons.pause : Icons.play_arrow),
                    ),
                  ),
                )
              else
                Card(
                  child: ListTile(
                    leading: Icon(
                      isVideo
                          ? Icons.ondemand_video_outlined
                          : Icons.library_music_outlined,
                    ),
                    title: Text(
                      isVideo
                          ? 'Video đang được bổ sung'
                          : 'Audio đang được bổ sung',
                    ),
                    subtitle: Text(
                      'Bài học đã có nội dung và transcript; media sẽ được gắn từ thư viện chuẩn.',
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
                  'Transcript nghe',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(transcript),
                  ),
                ),
              ],
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
