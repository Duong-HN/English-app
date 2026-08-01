import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/ocr_service.dart';
import '../../core/speech_service.dart';
import '../classes/classes_page.dart';
import '../content/curriculum_page.dart';
import '../settings/notifications_page.dart';
import '../settings/settings_page.dart';
import '../shared/learnmate_top_bar.dart';
import '../vocabulary/vocabulary_detail_page.dart';
import 'dashboard_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.apiClient,
    required this.authController,
    this.ocrService,
    this.speechService,
  });

  final ApiClient apiClient;
  final AuthController authController;
  final OcrService? ocrService;
  final SpeechService? speechService;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _dashboardKey = GlobalKey<DashboardPageState>();
  final _studyKey = GlobalKey<_StudyPageState>();
  final _learningPathKey = GlobalKey<_LearningPathPageState>();
  final _historyKey = GlobalKey<_HistoryPageState>();
  final _classesKey = GlobalKey<ClassesPageState>();
  late final OcrService _ocrService;
  late final SpeechService _speechService;
  late final List<Widget> _pages;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _ocrService = widget.ocrService ?? MlKitOcrService();
    _speechService = widget.speechService ?? DeviceSpeechService();
    _pages = [
      DashboardPage(
        key: _dashboardKey,
        apiClient: widget.apiClient,
        displayName:
            widget.authController.user?['display_name']?.toString() ?? 'bạn',
        onOpenLearningPath: _openLearningPath,
        onOpenCurriculum: _openCurriculum,
        onOpenClasses: () => _selectPage(2),
        onOpenStudy: _openStudyTask,
      ),
      _StudyPage(
        key: _studyKey,
        apiClient: widget.apiClient,
        ocrService: _ocrService,
        speechService: _speechService,
      ),
      ClassesPage(
        key: _classesKey,
        apiClient: widget.apiClient,
        authController: widget.authController,
      ),
      _HistoryPage(key: _historyKey, apiClient: widget.apiClient),
      _ProfilePage(authController: widget.authController),
    ];
  }

  void _selectPage(int index) {
    if (index == 1) _studyKey.currentState?.setTaskContext(null);
    setState(() => _selectedIndex = index);
    if (index == 0) _dashboardKey.currentState?.refresh();
    if (index == 3) _historyKey.currentState?.refresh();
  }

  void _openStudyTask(Map<String, dynamic>? task) {
    _studyKey.currentState?.setTaskContext(task);
    setState(() => _selectedIndex = 1);
  }

  Future<void> _openLearningPath() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => Scaffold(
          appBar: AppBar(title: const Text('Lộ trình cá nhân')),
          body: SafeArea(
            child: _LearningPathPage(
              key: _learningPathKey,
              apiClient: widget.apiClient,
            ),
          ),
        ),
      ),
    );
    if (mounted) _dashboardKey.currentState?.refresh();
  }

  Future<void> _openCurriculum() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CurriculumPage(apiClient: widget.apiClient),
      ),
    );
    if (mounted) _dashboardKey.currentState?.refresh();
  }

  Future<void> _openSettings() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SettingsPage(authController: widget.authController),
      ),
    );
    if (mounted) {
      _dashboardKey.currentState?.refresh();
      _classesKey.currentState?.refresh();
      setState(() {});
    }
  }

  Future<void> _openNotifications() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => NotificationsPage(apiClient: widget.apiClient),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    const titles = ['Tổng quan', 'Học tập', 'Lớp học', 'Lịch sử', 'Hồ sơ'];
    return Scaffold(
      appBar: LearnMateTopBar(
        authController: widget.authController,
        title: titles[_selectedIndex],
        onSettings: _openSettings,
        onNotifications: _openNotifications,
      ),
      body: SafeArea(
        child: IndexedStack(index: _selectedIndex, children: _pages),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        minimum: const EdgeInsets.fromLTRB(12, 0, 12, 10),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(24),
            boxShadow: const [
              BoxShadow(
                color: Color(0x1A0F172A),
                blurRadius: 24,
                offset: Offset(0, 8),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: NavigationBar(
              height: 72,
              elevation: 0,
              backgroundColor: Colors.transparent,
              indicatorColor: Theme.of(context).colorScheme.primaryContainer,
              selectedIndex: _selectedIndex,
              onDestinationSelected: _selectPage,
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.home_outlined),
                  selectedIcon: Icon(Icons.home_rounded),
                  label: 'Home',
                ),
                NavigationDestination(
                  icon: Icon(Icons.school_outlined),
                  selectedIcon: Icon(Icons.school_rounded),
                  label: 'Học',
                ),
                NavigationDestination(
                  icon: Icon(Icons.groups_outlined),
                  selectedIcon: Icon(Icons.groups_rounded),
                  label: 'Lớp',
                ),
                NavigationDestination(
                  icon: Icon(Icons.history_outlined),
                  selectedIcon: Icon(Icons.history_rounded),
                  label: 'Lịch sử',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline_rounded),
                  selectedIcon: Icon(Icons.person_rounded),
                  label: 'Hồ sơ',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _LearningPathPage extends StatefulWidget {
  const _LearningPathPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<_LearningPathPage> createState() => _LearningPathPageState();
}

class _LearningPathPageState extends State<_LearningPathPage> {
  final _goalController = TextEditingController(
    text: 'Giao tiếp tiếng Anh tự tin trong học tập và công việc',
  );
  Map<String, dynamic>? _learningPath;
  String _level = 'B1';
  int _minutes = 30;
  bool _loading = true;
  bool _generating = false;
  String _generationStatus = 'idle';
  bool _placementSubmitting = false;
  bool _adapting = false;
  int? _progressDay;
  List<Map<String, dynamic>>? _placementQuestions;
  final Map<String, String> _placementAnswers = {};
  Map<String, dynamic>? _placementResult;
  String? _error;

  @override
  void initState() {
    super.initState();
    refresh();
  }

  @override
  void dispose() {
    _goalController.dispose();
    super.dispose();
  }

  Future<void> refresh() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final result = await widget.apiClient.currentLearningPath();
      if (!mounted) return;
      setState(() {
        _learningPath = result;
        _placementQuestions = null;
        _goalController.text =
            result['goal']?.toString() ?? _goalController.text;
        _level = result['current_level']?.toString() ?? _level;
        _minutes = result['minutes_per_day'] as int? ?? _minutes;
      });
    } on ApiException catch (exception) {
      if (!mounted) return;
      if (exception.statusCode == 404) {
        setState(() => _learningPath = null);
        try {
          final placement = await widget.apiClient.latestPlacementResult();
          if (mounted) {
            setState(() {
              _placementResult = placement;
              _level = placement['level']?.toString() ?? _level;
            });
          }
        } on ApiException catch (placementException) {
          if (placementException.statusCode != 404 && mounted) {
            setState(() => _error = placementException.message);
          }
        }
        try {
          final test = await widget.apiClient.placementTest();
          if (mounted) {
            setState(() {
              _placementQuestions =
                  (test['questions'] as List<dynamic>? ?? const [])
                      .whereType<Map<String, dynamic>>()
                      .toList();
            });
          }
        } catch (_) {
          // Keep the existing path form usable if the optional placement screen fails to load.
        }
      } else {
        setState(() => _error = exception.message);
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể tải lộ trình học.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _generate() async {
    final goal = _goalController.text.trim();
    if (goal.length < 3) {
      setState(() => _error = 'Hãy nhập mục tiêu học cụ thể.');
      return;
    }
    setState(() {
      _generating = true;
      _error = null;
      _generationStatus = 'processing';
    });
    try {
      final result = await widget.apiClient.generateLearningPath(
        goal: goal,
        currentLevel: _level,
        minutesPerDay: _minutes,
        onStatus: (status) {
          if (mounted) setState(() => _generationStatus = status);
        },
      );
      if (mounted) {
        setState(() {
          _learningPath = result;
          _generationStatus = 'succeeded';
        });
      }
    } on ApiException catch (exception) {
      if (mounted) {
        setState(() {
          _generationStatus = 'failed';
          _error = exception.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _generationStatus = 'failed';
          _error = 'Không thể kết nối máy chủ.';
        });
      }
    } finally {
      if (mounted) setState(() => _generating = false);
    }
  }

  Future<void> _submitPlacement() async {
    if (_placementQuestions == null ||
        _placementAnswers.length != _placementQuestions!.length) {
      setState(() => _error = 'Hãy trả lời đủ các câu hỏi trước khi nộp bài.');
      return;
    }
    setState(() {
      _placementSubmitting = true;
      _error = null;
    });
    try {
      final result = await widget.apiClient.submitPlacementTest(
        _placementAnswers,
      );
      if (!mounted) return;
      setState(() {
        _placementResult = result;
        _level = result['level']?.toString() ?? _level;
        _placementQuestions = null;
      });
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } finally {
      if (mounted) setState(() => _placementSubmitting = false);
    }
  }

  Future<void> _toggleDay(int day, bool completed) async {
    final path = _learningPath;
    if (path == null) return;
    setState(() => _progressDay = day);
    try {
      final result = await widget.apiClient.updateDailyProgress(
        learningPathId: path['id'].toString(),
        day: day,
        completed: completed,
      );
      if (mounted) setState(() => _learningPath = result);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } finally {
      if (mounted) setState(() => _progressDay = null);
    }
  }

  Future<void> _adapt() async {
    final path = _learningPath;
    if (path == null) return;
    setState(() {
      _adapting = true;
      _error = null;
    });
    try {
      final result = await widget.apiClient.adaptLearningPath(
        path['id'].toString(),
      );
      if (mounted) setState(() => _learningPath = result);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } finally {
      if (mounted) setState(() => _adapting = false);
    }
  }

  List<Map<String, dynamic>> _items(Map<String, dynamic> plan, String key) {
    return (plan[key] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final plan = _learningPath?['plan'] as Map<String, dynamic>?;
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
        children: [
          Text(
            'Lộ trình cá nhân',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          const Text(
            'Tạo kế hoạch 7 ngày từ mục tiêu và các bài đã thực hành.',
          ),
          const SizedBox(height: 18),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    key: const Key('learning-path-goal'),
                    controller: _goalController,
                    maxLength: 240,
                    decoration: const InputDecoration(
                      labelText: 'Mục tiêu học',
                      hintText: 'Ví dụ: giao tiếp trong phỏng vấn xin việc',
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          key: ValueKey('learning-path-level-$_level'),
                          initialValue: _level,
                          decoration: const InputDecoration(
                            labelText: 'Trình độ hiện tại',
                          ),
                          items: const ['A1', 'A2', 'B1', 'B2', 'C1']
                              .map(
                                (value) => DropdownMenuItem(
                                  value: value,
                                  child: Text(value),
                                ),
                              )
                              .toList(),
                          onChanged: (value) {
                            if (value != null) setState(() => _level = value);
                          },
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: DropdownButtonFormField<int>(
                          key: ValueKey('learning-path-minutes-$_minutes'),
                          initialValue: _minutes,
                          decoration: const InputDecoration(
                            labelText: 'Phút mỗi ngày',
                          ),
                          items: const [15, 20, 30, 45, 60]
                              .map(
                                (value) => DropdownMenuItem(
                                  value: value,
                                  child: Text('$value phút'),
                                ),
                              )
                              .toList(),
                          onChanged: (value) {
                            if (value != null) setState(() => _minutes = value);
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      key: const Key('generate-learning-path'),
                      onPressed: _generating ? null : _generate,
                      icon: _generating
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.auto_awesome),
                      label: Text(
                        _generating
                            ? 'Đang tạo lộ trình...'
                            : 'Tạo lộ trình 7 ngày',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_generationStatus != 'idle') ...[
            const SizedBox(height: 14),
            _LearningPathStatusCard(
              status: _generationStatus,
              onRetry: _generationStatus == 'failed' && !_generating
                  ? _generate
                  : null,
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 14),
            _MessageCard(message: _error!, isError: true),
          ],
          if (_loading) ...[
            const SizedBox(height: 24),
            const Center(child: CircularProgressIndicator()),
          ] else if (plan == null) ...[
            const SizedBox(height: 14),
            if (_placementQuestions != null)
              _PlacementTestCard(
                questions: _placementQuestions!,
                answers: _placementAnswers,
                submitting: _placementSubmitting,
                result: _placementResult,
                onAnswer: (id, answer) {
                  setState(() => _placementAnswers[id] = answer);
                },
                onSubmit: _submitPlacement,
              ),
            const _MessageCard(
              message:
                  'Chưa có lộ trình. Chọn mục tiêu và tạo kế hoạch đầu tiên.',
            ),
          ] else ...[
            const SizedBox(height: 14),
            _LearningPathResultCard(
              learningPath: _learningPath!,
              tasks: _items(plan, 'daily_tasks'),
              progressDay: _progressDay,
              adapting: _adapting,
              onToggleDay: _toggleDay,
              onAdapt: _adapt,
            ),
          ],
        ],
      ),
    );
  }
}

class _LearningPathStatusCard extends StatelessWidget {
  const _LearningPathStatusCard({required this.status, this.onRetry});

  final String status;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final label = switch (status) {
      'succeeded' => 'Thành công',
      'failed' => 'Thất bại',
      _ => 'Đang xử lý',
    };
    final icon = switch (status) {
      'succeeded' => Icons.check_circle,
      'failed' => Icons.error_outline,
      _ => Icons.hourglass_top,
    };
    final color = switch (status) {
      'succeeded' => Colors.green,
      'failed' => Colors.red,
      _ => Colors.orange,
    };
    return Semantics(
      liveRegion: true,
      label: 'Trạng thái tạo lộ trình: $label',
      child: Card(
        key: const Key('learning-path-status'),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(color: color, fontWeight: FontWeight.w600),
                ),
              ),
              if (onRetry != null)
                TextButton(onPressed: onRetry, child: const Text('Thử lại')),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlacementTestCard extends StatelessWidget {
  const _PlacementTestCard({
    required this.questions,
    required this.answers,
    required this.submitting,
    required this.result,
    required this.onAnswer,
    required this.onSubmit,
  });

  final List<Map<String, dynamic>> questions;
  final Map<String, String> answers;
  final bool submitting;
  final Map<String, dynamic>? result;
  final void Function(String id, String answer) onAnswer;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Placement test',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            const Text(
              'Làm bài kiểm tra ngắn để chọn trình độ bắt đầu phù hợp. Kết quả chỉ là ước lượng học tập, không phải chứng chỉ CEFR.',
            ),
            const SizedBox(height: 14),
            ...questions.map((question) {
              final id = question['id'].toString();
              final options =
                  (question['options'] as List<dynamic>? ?? const [])
                      .map((option) => option.toString())
                      .toList();
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${questions.indexOf(question) + 1}. ${question['prompt']}',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  RadioGroup<String>(
                    groupValue: answers[id],
                    onChanged: (value) {
                      if (value != null) onAnswer(id, value);
                    },
                    child: Column(
                      children: options
                          .asMap()
                          .entries
                          .map(
                            (entry) => RadioListTile<String>(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              value: String.fromCharCode(97 + entry.key),
                              title: Text(entry.value),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                  const SizedBox(height: 8),
                ],
              );
            }),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: submitting ? null : onSubmit,
                icon: submitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.fact_check_outlined),
                label: Text(
                  submitting ? 'Đang chấm bài...' : 'Nộp placement test',
                ),
              ),
            ),
            if (result != null) ...[
              const SizedBox(height: 10),
              Text(
                'Trình độ ước lượng: ${result!['level']} (${result!['score']}/${result!['total_questions']})',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LearningPathResultCard extends StatelessWidget {
  const _LearningPathResultCard({
    required this.learningPath,
    required this.tasks,
    required this.progressDay,
    required this.adapting,
    required this.onToggleDay,
    required this.onAdapt,
  });

  final Map<String, dynamic> learningPath;
  final List<Map<String, dynamic>> tasks;
  final int? progressDay;
  final bool adapting;
  final void Function(int day, bool completed) onToggleDay;
  final VoidCallback onAdapt;

  List<String> _strings(Map<String, dynamic> plan, String key) {
    return (plan[key] as List<dynamic>? ?? const [])
        .map((item) => item.toString())
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final plan = learningPath['plan'] as Map<String, dynamic>;
    final focusAreas = _strings(plan, 'focus_areas');
    final notes = _strings(plan, 'personalization_notes');
    final checkpoints = _strings(plan, 'checkpoints');
    final progress =
        (learningPath['daily_progress'] as Map<dynamic, dynamic>?)?.map(
          (key, value) => MapEntry(key.toString(), value),
        ) ??
        <String, dynamic>{};
    final completedDays = progress.values
        .whereType<Map<dynamic, dynamic>>()
        .where((item) => item['completed'] == true)
        .length;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.route, color: Colors.indigo),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${learningPath['current_level']} · ${learningPath['minutes_per_day']} phút/ngày',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(plan['summary']?.toString() ?? ''),
            const SizedBox(height: 12),
            Row(
              children: [
                Text('Tiến độ: $completedDays/${tasks.length} ngày'),
                const Spacer(),
                OutlinedButton.icon(
                  onPressed: adapting ? null : onAdapt,
                  icon: adapting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.sync),
                  label: const Text('Điều chỉnh'),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Text('Trọng tâm', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: focusAreas
                  .map((item) => Chip(label: Text(item)))
                  .toList(),
            ),
            if (notes.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                'Vì sao lộ trình này phù hợp',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              ...notes.map(
                (note) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.insights_outlined, size: 20),
                  title: Text(note),
                ),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              'Nhiệm vụ 7 ngày',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            ...tasks.map(
              (task) => ExpansionTile(
                tilePadding: EdgeInsets.zero,
                leading: CircleAvatar(
                  radius: 16,
                  child: Text('${task['day']}'),
                ),
                title: Text(task['title']?.toString() ?? 'Nhiệm vụ'),
                subtitle: Text(
                  '${task['duration_minutes']} phút · ${task['skill']}',
                ),
                trailing: Checkbox(
                  value:
                      ((progress[task['day'].toString()]
                          as Map?)?['completed']) ==
                      true,
                  onChanged: progressDay == task['day']
                      ? null
                      : (value) =>
                            onToggleDay(task['day'] as int, value ?? false),
                ),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Padding(
                      padding: const EdgeInsets.only(left: 48, bottom: 14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(task['activity']?.toString() ?? ''),
                          const SizedBox(height: 6),
                          Text(
                            'Hoàn thành khi: ${task['success_criteria']}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (checkpoints.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Mốc kiểm tra',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              ...checkpoints.map(
                (item) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.flag_outlined, size: 20),
                  title: Text(item),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StudyPage extends StatefulWidget {
  const _StudyPage({
    super.key,
    required this.apiClient,
    required this.ocrService,
    required this.speechService,
  });

  final ApiClient apiClient;
  final OcrService ocrService;
  final SpeechService speechService;

  @override
  State<_StudyPage> createState() => _StudyPageState();
}

class _StudyPageState extends State<_StudyPage> {
  final _textController = TextEditingController();
  String _mode = 'reading';
  Map<String, dynamic>? _taskContext;
  Map<String, dynamic>? _result;
  bool _taskProgressRecorded = false;
  bool _loading = false;
  bool _capturing = false;
  bool _listening = false;
  String _analysisStatus = 'idle';
  String? _error;

  void setTaskContext(Map<String, dynamic>? task) {
    widget.speechService.stop();
    final requestedSkill = task?['skill']?.toString().toLowerCase();
    final mode =
        const {'reading', 'writing', 'speaking'}.contains(requestedSkill)
        ? requestedSkill!
        : _mode;
    setState(() {
      _taskContext = task == null ? null : Map<String, dynamic>.from(task);
      _mode = mode;
      _result = null;
      _error = null;
      _analysisStatus = 'idle';
      _listening = false;
      _taskProgressRecorded = false;
      if (task != null) _textController.clear();
    });
  }

  @override
  void dispose() {
    widget.speechService.stop();
    _textController.dispose();
    super.dispose();
  }

  Future<void> _analyze() async {
    final text = _textController.text.trim();
    if (text.isEmpty) {
      setState(() => _error = 'Hãy nhập một đoạn tiếng Anh trước.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
      _analysisStatus = 'processing';
    });
    try {
      final learningPathId = _taskText(const [
        'learning_path_id',
        'learningPathId',
      ]);
      final taskDay = _taskInt(const ['day', 'task_day', 'taskDay']);
      final response = await widget.apiClient.analyze(
        type: _mode,
        inputText: text,
        learningPathId: learningPathId,
        taskDay: taskDay,
        onStatus: (status) {
          if (mounted) setState(() => _analysisStatus = status);
        },
      );
      if (mounted) {
        setState(() {
          _result = response['result'] as Map<String, dynamic>;
          _analysisStatus = 'succeeded';
          _taskProgressRecorded = learningPathId != null && taskDay != null;
        });
      }
    } on ApiException catch (exception) {
      if (mounted) {
        setState(() {
          _analysisStatus = 'failed';
          _error = exception.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _analysisStatus = 'failed');
        setState(() => _error = 'Không thể kết nối máy chủ.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _scan(ImageSource source) async {
    setState(() {
      _capturing = true;
      _error = null;
    });
    try {
      final text = await widget.ocrService.recognize(source);
      if (!mounted || text == null) return;
      if (text.isEmpty) {
        setState(() => _error = 'Không tìm thấy chữ trong ảnh.');
      } else {
        _textController.text = text;
        setState(() => _result = null);
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _capturing = false);
    }
  }

  Future<void> _toggleSpeech() async {
    if (_listening) {
      await widget.speechService.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }
    setState(() => _error = null);
    try {
      final started = await widget.speechService.start(
        onText: (text) {
          if (!mounted) return;
          _textController.text = text;
          _textController.selection = TextSelection.collapsed(
            offset: text.length,
          );
          setState(() => _listening = widget.speechService.isListening);
        },
        onError: (message) {
          if (mounted) {
            setState(() {
              _error = message;
              _listening = false;
            });
          }
        },
        onListeningChanged: (listening) {
          if (mounted) setState(() => _listening = listening);
        },
      );
      if (mounted) setState(() => _listening = started);
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = 'Không thể khởi động nhận dạng giọng nói: $error';
          _listening = false;
        });
      }
    }
  }

  void _changeMode(Set<String> selected) {
    widget.speechService.stop();
    setState(() {
      _mode = selected.first;
      _result = null;
      _error = null;
      _analysisStatus = 'idle';
      _listening = false;
    });
  }

  String? _taskText(List<String> keys) {
    final task = _taskContext;
    if (task == null) return null;
    for (final key in keys) {
      final value = task[key]?.toString().trim();
      if (value != null && value.isNotEmpty) return value;
    }
    return null;
  }

  int? _taskInt(List<String> keys) {
    final task = _taskContext;
    if (task == null) return null;
    for (final key in keys) {
      final value = task[key];
      if (value is int) return value;
      final parsed = int.tryParse(value?.toString() ?? '');
      if (parsed != null) return parsed;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('study-page'),
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
      children: [
        Text('Xin chào 👋', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 4),
        Text(
          'Học một chút tiếng Anh mỗi ngày',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
        if (_taskContext != null) ...[
          const SizedBox(height: 14),
          _PersonalTaskContextCard(
            task: _taskContext!,
            progressRecorded: _taskProgressRecorded,
          ),
        ],
        const SizedBox(height: 24),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Trợ lý học tập AI',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Nhận phản hồi có cấu trúc; điểm số chỉ mang tính tham khảo.',
                ),
                const SizedBox(height: 18),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(
                        value: 'reading',
                        label: Text('Đọc hiểu'),
                        icon: Icon(Icons.menu_book_outlined),
                      ),
                      ButtonSegment(
                        value: 'writing',
                        label: Text('Viết'),
                        icon: Icon(Icons.edit_outlined),
                      ),
                      ButtonSegment(
                        value: 'speaking',
                        label: Text('Nói'),
                        icon: Icon(Icons.mic_none),
                      ),
                    ],
                    selected: {_mode},
                    onSelectionChanged: _changeMode,
                  ),
                ),
                const SizedBox(height: 16),
                if (_mode == 'reading') _buildOcrActions(),
                if (_mode == 'speaking') _buildSpeechAction(),
                TextField(
                  key: const Key('study-input'),
                  controller: _textController,
                  minLines: 5,
                  maxLines: 10,
                  decoration: InputDecoration(
                    labelText: _mode == 'speaking'
                        ? 'Transcript câu trả lời'
                        : 'Nội dung tiếng Anh',
                    hintText: _mode == 'reading'
                        ? 'Chụp ảnh hoặc nhập đoạn văn...'
                        : _mode == 'writing'
                        ? 'Nhập bài viết của bạn...'
                        : 'Nhấn micro hoặc nhập câu trả lời...',
                    alignLabelWithHint: true,
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    key: const Key('analyze-study'),
                    onPressed: _loading ? null : _analyze,
                    icon: _loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.auto_awesome),
                    label: Text(
                      _loading ? 'Đang phân tích...' : 'Phân tích bằng AI',
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        if (_analysisStatus != 'idle') ...[
          const SizedBox(height: 10),
          _AnalysisStatusCard(
            status: _analysisStatus,
            onRetry: _analysisStatus == 'failed' && !_loading ? _analyze : null,
          ),
        ],
        if (_error != null) ...[
          const SizedBox(height: 14),
          _MessageCard(message: _error!, isError: true),
        ],
        if (_result != null) ...[
          const SizedBox(height: 14),
          _ResultCard(
            apiClient: widget.apiClient,
            result: _result!,
            type: _mode,
          ),
        ],
      ],
    );
  }

  Widget _buildOcrActions() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          OutlinedButton.icon(
            onPressed: _capturing ? null : () => _scan(ImageSource.camera),
            icon: const Icon(Icons.camera_alt_outlined),
            label: Text(_capturing ? 'Đang đọc ảnh...' : 'Chụp ảnh OCR'),
          ),
          OutlinedButton.icon(
            onPressed: _capturing ? null : () => _scan(ImageSource.gallery),
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('Chọn từ thư viện'),
          ),
        ],
      ),
    );
  }

  Widget _buildSpeechAction() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          FilledButton.tonalIcon(
            onPressed: _toggleSpeech,
            icon: Icon(_listening ? Icons.stop : Icons.mic),
            label: Text(_listening ? 'Dừng ghi' : 'Bắt đầu nói'),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _listening
                  ? 'Đang nhận dạng tiếng Anh...'
                  : 'Chấm nội dung transcript, không chấm phát âm.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _AnalysisStatusCard extends StatelessWidget {
  const _AnalysisStatusCard({required this.status, this.onRetry});

  final String status;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final label = switch (status) {
      'succeeded' => 'Thành công',
      'failed' => 'Thất bại',
      _ => 'Đang xử lý',
    };
    final icon = switch (status) {
      'succeeded' => Icons.check_circle,
      'failed' => Icons.error_outline,
      _ => Icons.hourglass_top,
    };
    final color = switch (status) {
      'succeeded' => Colors.green,
      'failed' => Colors.red,
      _ => Colors.orange,
    };
    return Semantics(
      liveRegion: true,
      label: 'Trạng thái phân tích: $label',
      child: Row(
        key: const Key('analysis-status'),
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              label,
              style: TextStyle(color: color, fontWeight: FontWeight.w600),
            ),
          ),
          if (onRetry != null)
            TextButton(onPressed: onRetry, child: const Text('Thử lại')),
        ],
      ),
    );
  }
}

class _PersonalTaskContextCard extends StatelessWidget {
  const _PersonalTaskContextCard({
    required this.task,
    required this.progressRecorded,
  });

  final Map<String, dynamic> task;
  final bool progressRecorded;

  @override
  Widget build(BuildContext context) {
    final title = task['title']?.toString() ?? 'Nhiệm vụ trong lộ trình';
    final activity = task['activity']?.toString();
    final successCriteria = task['success_criteria']?.toString();
    final skill = task['skill']?.toString();
    final day = task['day'];
    final minutes = task['duration_minutes'] ?? task['estimated_minutes'];
    return Card(
      key: const Key('personal-task-context'),
      color: progressRecorded
          ? Colors.green.shade50
          : Theme.of(context).colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  progressRecorded ? Icons.check_circle : Icons.route,
                  color: progressRecorded ? Colors.green : null,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    progressRecorded ? 'Đã ghi nhận tiến độ' : title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            if (progressRecorded) ...[const SizedBox(height: 4), Text(title)],
            if (activity != null && activity.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(activity),
            ],
            if (successCriteria != null && successCriteria.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                'Hoàn thành khi: $successCriteria',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (day != null || minutes != null || skill != null) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (day != null) Chip(label: Text('Ngày $day')),
                  if (minutes != null) Chip(label: Text('$minutes phút')),
                  if (skill != null) Chip(label: Text(skill)),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.apiClient,
    required this.result,
    required this.type,
  });

  final ApiClient apiClient;
  final Map<String, dynamic> result;
  final String type;

  List<Map<String, dynamic>> _items(String key) {
    return (result[key] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final vocabulary = _items('vocabulary');
    final issues = _items('issues');
    final questions = _items('questions');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.check_circle, color: Colors.green),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Kết quả ${type == 'reading'
                        ? 'đọc hiểu'
                        : type == 'writing'
                        ? 'bài viết'
                        : 'luyện nói'}',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            if (result['score'] != null) ...[
              const SizedBox(height: 14),
              Text(
                'Điểm tham khảo: ${result['score']}/10',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ],
            if (result['summary'] != null) ...[
              const SizedBox(height: 12),
              Text(result['summary'].toString()),
            ],
            if (result['translation'] != null) ...[
              const SizedBox(height: 14),
              Text('Bản dịch', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 4),
              Text(result['translation'].toString()),
            ],
            if (issues.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                'Điểm cần cải thiện',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              ...issues.map(
                (item) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  leading: const Icon(Icons.lightbulb_outline, size: 20),
                  title: Text(item['title']?.toString() ?? 'Gợi ý'),
                  subtitle: Text(item['explanation']?.toString() ?? ''),
                ),
              ),
            ],
            if (vocabulary.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Từ vựng', style: Theme.of(context).textTheme.titleSmall),
              if (type == 'reading')
                const Text('Các từ này đã được lưu vào Flashcards của bạn.'),
              const SizedBox(height: 6),
              ...vocabulary.map(
                (item) =>
                    _VocabularyFlashcard(apiClient: apiClient, item: item),
              ),
            ],
            if (questions.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                'Câu hỏi đọc hiểu',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              ...questions.map(
                (item) => ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: Text(item['question']?.toString() ?? ''),
                  children: [
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Text('Đáp án: ${item['answer']}'),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (result['rewrite'] != null) ...[
              const SizedBox(height: 14),
              Text(
                'Gợi ý viết lại',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 4),
              SelectableText(result['rewrite'].toString()),
            ],
            if (result['pronunciation_note'] != null) ...[
              const SizedBox(height: 14),
              Text(
                result['pronunciation_note'].toString(),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _VocabularyFlashcard extends StatelessWidget {
  const _VocabularyFlashcard({required this.apiClient, required this.item});

  final ApiClient apiClient;
  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final word = item['word']?.toString().trim() ?? '';
    final meaning = item['meaning']?.toString().trim() ?? '';
    final example = item['example']?.toString().trim() ?? '';
    return Card(
      key: Key('vocabulary-flashcard-$word'),
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      margin: const EdgeInsets.only(top: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 8, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(word, style: Theme.of(context).textTheme.titleMedium),
            if (meaning.isNotEmpty) ...[
              const SizedBox(height: 3),
              Text(meaning),
            ],
            if (example.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                example,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic),
              ),
            ],
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                key: Key('view-word-details-$word'),
                onPressed: word.isEmpty
                    ? null
                    : () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (context) => VocabularyDetailPage(
                              apiClient: apiClient,
                              word: word,
                            ),
                          ),
                        );
                      },
                icon: const Icon(Icons.menu_book_outlined),
                label: const Text('Xem chi tiết'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryPage extends StatefulWidget {
  const _HistoryPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<_HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<_HistoryPage> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.history();
  }

  Future<void> refresh() async {
    final next = widget.apiClient.history();
    setState(() {
      _future = next;
    });
    await next;
  }

  Future<void> _delete(String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xóa kết quả?'),
        content: const Text('Hành động này không thể hoàn tác.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.apiClient.deleteAnalysis(id);
      await refresh();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Không thể xóa: $error')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Lịch sử học tập',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 12),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return _MessageCard(
                  message: snapshot.error.toString(),
                  isError: true,
                );
              }
              final items = snapshot.data ?? const [];
              if (items.isEmpty) {
                return const _MessageCard(
                  message:
                      'Chưa có hoạt động nào. Hãy phân tích một đoạn văn trước.',
                );
              }
              return Column(
                children: items
                    .map(
                      (item) => Card(
                        child: ListTile(
                          leading: Icon(
                            item['type'] == 'writing'
                                ? Icons.edit
                                : item['type'] == 'speaking'
                                ? Icons.mic
                                : Icons.menu_book,
                          ),
                          title: Text(item['type'].toString().toUpperCase()),
                          subtitle: Text(
                            item['input_text'].toString(),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (item['score'] != null)
                                Text('${item['score']}/10'),
                              IconButton(
                                tooltip: 'Xóa',
                                onPressed: () => _delete(item['id'].toString()),
                                icon: const Icon(Icons.delete_outline),
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                    .toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _ProfilePage extends StatelessWidget {
  const _ProfilePage({required this.authController});

  final AuthController authController;

  @override
  Widget build(BuildContext context) {
    final user = authController.user ?? const <String, dynamic>{};
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text('Hồ sơ', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        Card(
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.person)),
            title: Text(user['display_name']?.toString() ?? 'Learner'),
            subtitle: Text(user['email']?.toString() ?? ''),
          ),
        ),
        const SizedBox(height: 12),
        const Card(
          child: ListTile(
            leading: Icon(Icons.verified_user_outlined),
            title: Text('Dữ liệu cá nhân'),
            subtitle: Text(
              'Access token được lưu trong secure storage; API key AI chỉ nằm ở backend.',
            ),
          ),
        ),
        const SizedBox(height: 20),
        const Card(
          child: ListTile(
            leading: Icon(Icons.settings_outlined),
            title: Text('Tùy chỉnh tài khoản'),
            subtitle: Text(
              'Mở Cài đặt ở góc trên bên trái để đổi chế độ hoặc đăng ký giáo viên.',
            ),
          ),
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: authController.logout,
          icon: const Icon(Icons.logout),
          label: const Text('Đăng xuất'),
        ),
      ],
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({required this.message, this.isError = false});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: isError ? Colors.red.shade50 : null,
      child: Padding(padding: const EdgeInsets.all(16), child: Text(message)),
    );
  }
}
