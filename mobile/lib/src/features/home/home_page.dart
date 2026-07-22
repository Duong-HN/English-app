import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/ocr_service.dart';
import '../../core/speech_service.dart';
import '../classes/classes_page.dart';

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
  final _learningPathKey = GlobalKey<_LearningPathPageState>();
  final _classesKey = GlobalKey<ClassesPageState>();
  final _historyKey = GlobalKey<_HistoryPageState>();
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
      _StudyPage(
        apiClient: widget.apiClient,
        ocrService: _ocrService,
        speechService: _speechService,
      ),
      _LearningPathPage(key: _learningPathKey, apiClient: widget.apiClient),
      ClassesPage(
        key: _classesKey,
        apiClient: widget.apiClient,
        isLearner: widget.authController.user?['role'] == 'learner',
      ),
      _HistoryPage(key: _historyKey, apiClient: widget.apiClient),
      _ProfilePage(authController: widget.authController),
    ];
  }

  void _selectPage(int index) {
    setState(() => _selectedIndex = index);
    if (index == 1) _learningPathKey.currentState?.refresh();
    if (index == 2) _classesKey.currentState?.refresh();
    if (index == 3) _historyKey.currentState?.refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: IndexedStack(index: _selectedIndex, children: _pages),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _selectPage,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.school_outlined),
            selectedIcon: Icon(Icons.school),
            label: 'Học',
          ),
          NavigationDestination(
            icon: Icon(Icons.route_outlined),
            selectedIcon: Icon(Icons.route),
            label: 'Lộ trình',
          ),
          NavigationDestination(
            key: Key('classes-tab'),
            icon: Icon(Icons.groups_outlined),
            selectedIcon: Icon(Icons.groups),
            label: 'Lớp học',
          ),
          NavigationDestination(icon: Icon(Icons.history), label: 'Lịch sử'),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Hồ sơ',
          ),
        ],
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
        _goalController.text =
            result['goal']?.toString() ?? _goalController.text;
        _level = result['current_level']?.toString() ?? _level;
        _minutes = result['minutes_per_day'] as int? ?? _minutes;
      });
    } on ApiException catch (exception) {
      if (!mounted) return;
      if (exception.statusCode == 404) {
        setState(() => _learningPath = null);
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
    });
    try {
      final result = await widget.apiClient.generateLearningPath(
        goal: goal,
        currentLevel: _level,
        minutesPerDay: _minutes,
      );
      if (mounted) setState(() => _learningPath = result);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể kết nối máy chủ.');
    } finally {
      if (mounted) setState(() => _generating = false);
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
          if (_error != null) ...[
            const SizedBox(height: 14),
            _MessageCard(message: _error!, isError: true),
          ],
          if (_loading) ...[
            const SizedBox(height: 24),
            const Center(child: CircularProgressIndicator()),
          ] else if (plan == null) ...[
            const SizedBox(height: 14),
            const _MessageCard(
              message:
                  'Chưa có lộ trình. Chọn mục tiêu và tạo kế hoạch đầu tiên.',
            ),
          ] else ...[
            const SizedBox(height: 14),
            _LearningPathResultCard(
              learningPath: _learningPath!,
              tasks: _items(plan, 'daily_tasks'),
            ),
          ],
        ],
      ),
    );
  }
}

class _LearningPathResultCard extends StatelessWidget {
  const _LearningPathResultCard({
    required this.learningPath,
    required this.tasks,
  });

  final Map<String, dynamic> learningPath;
  final List<Map<String, dynamic>> tasks;

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
  Map<String, dynamic>? _result;
  bool _loading = false;
  bool _capturing = false;
  bool _listening = false;
  String? _error;

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
    });
    try {
      final response = await widget.apiClient.analyze(
        type: _mode,
        inputText: text,
      );
      if (mounted) {
        setState(() => _result = response['result'] as Map<String, dynamic>);
      }
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) {
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
      _listening = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
      children: [
        Text('Xin chào 👋', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 4),
        Text(
          'Học một chút tiếng Anh mỗi ngày',
          style: Theme.of(context).textTheme.bodyLarge,
        ),
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
        if (_error != null) ...[
          const SizedBox(height: 14),
          _MessageCard(message: _error!, isError: true),
        ],
        if (_result != null) ...[
          const SizedBox(height: 14),
          _ResultCard(result: _result!, type: _mode),
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

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result, required this.type});

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
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: vocabulary
                    .map(
                      (item) => Chip(
                        label: Text('${item['word']}: ${item['meaning']}'),
                      ),
                    )
                    .toList(),
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
    setState(() => _future = next);
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
