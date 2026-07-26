import 'package:flutter/material.dart';

import '../../core/api_client.dart';

class ClassesPage extends StatefulWidget {
  const ClassesPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<ClassesPage> createState() => _ClassesPageState();
}

class _ClassesPageState extends State<ClassesPage> {
  final _inviteController = TextEditingController();
  late Future<List<Map<String, dynamic>>> _future;
  bool _joining = false;
  String? _joinError;

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.classes();
  }

  @override
  void dispose() {
    _inviteController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.classes();
    setState(() {
      _future = next;
    });
    await next;
  }

  Future<void> _join() async {
    final code = _inviteController.text.trim();
    if (code.length < 6) {
      setState(() => _joinError = 'Mã mời cần có ít nhất 6 ký tự.');
      return;
    }
    setState(() {
      _joining = true;
      _joinError = null;
    });
    try {
      await widget.apiClient.joinClass(code);
      _inviteController.clear();
      await _refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã tham gia lớp thành công.')),
      );
    } on ApiException catch (exception) {
      if (mounted) setState(() => _joinError = exception.message);
    } catch (_) {
      if (mounted) setState(() => _joinError = 'Không thể tham gia lớp.');
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
        children: [
          Text('Lớp học', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          const Text('Nhận bài từ giáo viên và vẫn học theo lộ trình riêng.'),
          const SizedBox(height: 18),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Tham gia lớp mới',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    key: const Key('class-invite-code'),
                    controller: _inviteController,
                    textCapitalization: TextCapitalization.characters,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _joining ? null : _join(),
                    decoration: const InputDecoration(
                      labelText: 'Mã mời',
                      hintText: 'Ví dụ: IELTS01',
                      prefixIcon: Icon(Icons.vpn_key_outlined),
                    ),
                  ),
                  if (_joinError != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _joinError!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    key: const Key('join-class'),
                    onPressed: _joining ? null : _join,
                    icon: _joining
                        ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.group_add_outlined),
                    label: Text(_joining ? 'Đang tham gia...' : 'Tham gia lớp'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('Lớp của tôi', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (snapshot.hasError) {
                return _NoticeCard(
                  message: _errorText(snapshot.error),
                  error: true,
                  actionLabel: 'Tải lại',
                  onAction: _refresh,
                );
              }
              final classes = snapshot.data ?? const [];
              if (classes.isEmpty) {
                return const _NoticeCard(
                  message:
                      'Bạn chưa tham gia lớp nào. Nhập mã mời do giáo viên cung cấp để bắt đầu.',
                );
              }
              return Column(
                children: classes
                    .map(
                      (item) => _ClassCard(
                        item: item,
                        onOpen: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => ClassAssignmentsPage(
                              apiClient: widget.apiClient,
                              classData: item,
                            ),
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

class _ClassCard extends StatelessWidget {
  const _ClassCard({required this.item, required this.onOpen});

  final Map<String, dynamic> item;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final teacher = _firstText(item, const [
      'teacher_name',
      'teacher_display_name',
      'teacher',
    ]);
    final assignmentCount = _firstInt(item, const [
      'pending_assignments',
      'assignment_count',
      'assignments_count',
    ]);
    return Card(
      child: ListTile(
        onTap: onOpen,
        leading: const CircleAvatar(child: Icon(Icons.groups_outlined)),
        title: Text(_firstText(item, const ['name', 'title']) ?? 'Lớp học'),
        subtitle: Text(
          [
            if (teacher != null) 'GV: $teacher',
            if (assignmentCount != null) '$assignmentCount bài tập',
          ].join(' · '),
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}

class ClassAssignmentsPage extends StatefulWidget {
  const ClassAssignmentsPage({
    super.key,
    required this.apiClient,
    required this.classData,
  });

  final ApiClient apiClient;
  final Map<String, dynamic> classData;

  @override
  State<ClassAssignmentsPage> createState() => _ClassAssignmentsPageState();
}

class _ClassAssignmentsPageState extends State<ClassAssignmentsPage> {
  late Future<List<Map<String, dynamic>>> _future;

  String get _classId =>
      _firstText(widget.classData, const ['id', 'class_id']) ?? '';

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.classAssignments(_classId);
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.classAssignments(_classId);
    setState(() {
      _future = next;
    });
    await next;
  }

  @override
  Widget build(BuildContext context) {
    final name =
        _firstText(widget.classData, const ['name', 'title']) ?? 'Lớp học';
    return Scaffold(
      appBar: AppBar(title: Text(name)),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              'Bài tập từ giáo viên',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            FutureBuilder<List<Map<String, dynamic>>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                if (snapshot.hasError) {
                  return _NoticeCard(
                    message: _errorText(snapshot.error),
                    error: true,
                    actionLabel: 'Tải lại',
                    onAction: _refresh,
                  );
                }
                final assignments = snapshot.data ?? const [];
                if (assignments.isEmpty) {
                  return const _NoticeCard(
                    message: 'Giáo viên chưa giao bài tập cho lớp này.',
                  );
                }
                return Column(
                  children: assignments
                      .map(
                        (assignment) => _AssignmentCard(
                          assignment: assignment,
                          onOpen: () async {
                            await Navigator.of(context).push(
                              MaterialPageRoute<void>(
                                builder: (_) => AssignmentSubmissionPage(
                                  apiClient: widget.apiClient,
                                  assignment: assignment,
                                ),
                              ),
                            );
                            if (mounted) _refresh();
                          },
                        ),
                      )
                      .toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _AssignmentCard extends StatelessWidget {
  const _AssignmentCard({required this.assignment, required this.onOpen});

  final Map<String, dynamic> assignment;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final due = _firstText(assignment, const ['due_at', 'deadline']);
    final status = _firstText(assignment, const [
      'submission_status',
      'status',
    ]);
    final completed = const {
      'submitted',
      'reviewed',
      'completed',
    }.contains(status?.toLowerCase());
    return Card(
      child: ListTile(
        onTap: onOpen,
        leading: Icon(
          completed ? Icons.check_circle : Icons.assignment_outlined,
          color: completed ? Colors.green : null,
        ),
        title: Text(
          _firstText(assignment, const ['title', 'name']) ?? 'Bài tập',
        ),
        subtitle: Text(
          [
            if (_firstText(assignment, const ['skill', 'type'])
                case final skill?)
              _skillLabel(skill),
            if (due != null) 'Hạn: ${_shortDate(due)}',
            if (status != null) _statusLabel(status),
          ].join(' · '),
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}

class AssignmentSubmissionPage extends StatefulWidget {
  const AssignmentSubmissionPage({
    super.key,
    required this.apiClient,
    required this.assignment,
  });

  final ApiClient apiClient;
  final Map<String, dynamic> assignment;

  @override
  State<AssignmentSubmissionPage> createState() =>
      _AssignmentSubmissionPageState();
}

class _AssignmentSubmissionPageState extends State<AssignmentSubmissionPage> {
  final _textController = TextEditingController();
  bool _submitting = false;
  bool _loadingSubmission = false;
  String? _error;
  String? _loadError;
  Map<String, dynamic>? _submission;

  String get _assignmentId =>
      _firstText(widget.assignment, const ['id', 'assignment_id']) ?? '';

  @override
  void initState() {
    super.initState();
    _textController.text =
        _firstText(widget.assignment, const ['input_text', 'answer']) ?? '';
    final hasSubmission =
        _firstText(widget.assignment, const [
          'submission_id',
          'submission_status',
        ]) !=
        null;
    if (hasSubmission) {
      _loadingSubmission = true;
      _loadSubmission();
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  Future<void> _loadSubmission() async {
    if (mounted) {
      setState(() {
        _loadingSubmission = true;
        _loadError = null;
      });
    }
    try {
      final response = await widget.apiClient.assignmentSubmission(
        _assignmentId,
      );
      if (!mounted) return;
      final inputText = response['input_text']?.toString();
      setState(() {
        _submission = response;
        if (inputText != null) _textController.text = inputText;
      });
    } on ApiException catch (exception) {
      if (!mounted || exception.statusCode == 404) return;
      setState(() => _loadError = exception.message);
    } catch (_) {
      if (mounted) {
        setState(() => _loadError = 'Không thể tải bài đã nộp.');
      }
    } finally {
      if (mounted) setState(() => _loadingSubmission = false);
    }
  }

  Future<void> _submit() async {
    final text = _textController.text.trim();
    if (text.length < 3) {
      setState(() => _error = 'Bài làm cần có ít nhất 3 ký tự trước khi nộp.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
      _loadError = null;
    });
    try {
      final response = await widget.apiClient.submitAssignment(
        assignmentId: _assignmentId,
        inputText: text,
      );
      if (!mounted) return;
      setState(() => _submission = response);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Đã nộp bài.')));
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể nộp bài.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final title =
        _firstText(widget.assignment, const ['title', 'name']) ?? 'Bài tập';
    final instructions = _firstText(widget.assignment, const [
      'instructions',
      'content',
      'prompt',
      'description',
    ]);
    final feedbackSource = _submission ?? widget.assignment;
    final analysis = _asMap(
      feedbackSource['analysis'] ??
          feedbackSource['result'] ??
          feedbackSource['ai_feedback'],
    );
    final analysisResult = _asMap(analysis?['result']) ?? analysis;
    final teacherFeedback = _firstText(feedbackSource, const [
      'teacher_feedback',
      'feedback',
      'comment',
    ]);
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_loadingSubmission) ...[
            const LinearProgressIndicator(),
            const SizedBox(height: 12),
          ],
          if (_loadError != null) ...[
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: ListTile(
                title: Text(_loadError!),
                trailing: TextButton(
                  onPressed: _loadSubmission,
                  child: const Text('Thử lại'),
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (instructions != null) ...[
            Text('Yêu cầu', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(instructions),
              ),
            ),
            const SizedBox(height: 14),
          ],
          TextField(
            key: const Key('assignment-input'),
            controller: _textController,
            enabled: !_loadingSubmission,
            minLines: 7,
            maxLines: 16,
            decoration: const InputDecoration(
              labelText: 'Bài làm của bạn',
              hintText: 'Nhập câu trả lời bằng tiếng Anh...',
              alignLabelWithHint: true,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 12),
          FilledButton.icon(
            key: const Key('submit-assignment'),
            onPressed: _submitting || _loadingSubmission ? null : _submit,
            icon: _submitting
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send_outlined),
            label: Text(_submitting ? 'Đang nộp...' : 'Nộp bài'),
          ),
          if (analysisResult != null || teacherFeedback != null) ...[
            const SizedBox(height: 18),
            Text('Phản hồi', style: Theme.of(context).textTheme.titleLarge),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if ((analysis?['score'] ?? analysisResult?['score']) !=
                        null)
                      Text(
                        'Điểm tham khảo: ${analysis?['score'] ?? analysisResult!['score']}/10',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    if (analysisResult?['summary'] != null) ...[
                      const SizedBox(height: 8),
                      Text(analysisResult!['summary'].toString()),
                    ],
                    if (teacherFeedback != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        'Nhận xét của giáo viên',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      const SizedBox(height: 4),
                      Text(teacherFeedback),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _NoticeCard extends StatelessWidget {
  const _NoticeCard({
    required this.message,
    this.error = false,
    this.actionLabel,
    this.onAction,
  });

  final String message;
  final bool error;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: error ? Theme.of(context).colorScheme.errorContainer : null,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(message),
            if (actionLabel != null) ...[
              const SizedBox(height: 8),
              TextButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

Map<String, dynamic>? _asMap(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return null;
}

String? _firstText(Map<String, dynamic> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value == null) continue;
    if (value is Map) {
      final nested = value['display_name'] ?? value['name'] ?? value['title'];
      if (nested != null && nested.toString().trim().isNotEmpty) {
        return nested.toString();
      }
      continue;
    }
    final text = value.toString().trim();
    if (text.isNotEmpty) return text;
  }
  return null;
}

int? _firstInt(Map<String, dynamic> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is int) return value;
    final parsed = int.tryParse(value?.toString() ?? '');
    if (parsed != null) return parsed;
  }
  return null;
}

String _shortDate(String value) {
  final parsed = DateTime.tryParse(value)?.toLocal();
  if (parsed == null) return value;
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(parsed.day)}/${two(parsed.month)}/${parsed.year}';
}

String _skillLabel(String value) => switch (value.toLowerCase()) {
  'reading' => 'Đọc',
  'writing' => 'Viết',
  'speaking' => 'Nói',
  'listening' => 'Nghe',
  _ => value,
};

String _statusLabel(String value) => switch (value.toLowerCase()) {
  'submitted' => 'Đã nộp',
  'reviewed' => 'Đã nhận xét',
  'completed' => 'Hoàn thành',
  'pending' => 'Chưa nộp',
  _ => value,
};

String _errorText(Object? error) {
  if (error is ApiException) return error.message;
  return 'Không thể tải dữ liệu lớp học.';
}
