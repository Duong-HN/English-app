import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../classes/classes_page.dart';

class StudyGroupsPage extends StatefulWidget {
  const StudyGroupsPage({
    super.key,
    required this.apiClient,
    this.authController,
  });

  final ApiClient apiClient;
  final AuthController? authController;

  @override
  State<StudyGroupsPage> createState() => _StudyGroupsPageState();
}

class _StudyGroupsPageState extends State<StudyGroupsPage> {
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _inviteController = TextEditingController();
  late Future<List<Map<String, dynamic>>> _future;
  String _level = 'B1';
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.studyGroups();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _inviteController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.studyGroups();
    setState(() => _future = next);
    await next;
  }

  Future<void> _create() async {
    final name = _nameController.text.trim();
    if (name.length < 2) {
      setState(() => _error = 'Tên nhóm cần có ít nhất 2 ký tự.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final created = await widget.apiClient.createStudyGroup(
        name: name,
        description: _descriptionController.text,
        level: _level,
      );
      _nameController.clear();
      _descriptionController.clear();
      await _refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Đã tạo nhóm ${created['name'] ?? name}.')),
      );
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể tạo nhóm học tập.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _join() async {
    final code = _inviteController.text.trim();
    if (code.length < 6) {
      setState(() => _error = 'Mã mời cần có ít nhất 6 ký tự.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.apiClient.joinStudyGroup(code);
      _inviteController.clear();
      await _refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Đã tham gia nhóm học tập.')),
      );
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể tham gia nhóm.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _openGroup(Map<String, dynamic> group) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            StudyGroupDetailPage(apiClient: widget.apiClient, group: group),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Nhóm học tập')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
          children: [
            Text(
              'Học cùng bạn bè',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 4),
            const Text(
              'Tạo bài tập chung, chấm bài cho nhau và cùng leo bảng xếp hạng.',
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Tạo nhóm mới',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      key: const Key('study-group-name'),
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: 'Tên nhóm',
                        prefixIcon: Icon(Icons.groups_outlined),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _descriptionController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Mô tả ngắn',
                      ),
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      initialValue: _level,
                      decoration: const InputDecoration(
                        labelText: 'Cấp độ nhóm',
                      ),
                      items: const ['A1', 'A2', 'B1', 'B2', 'C1']
                          .map(
                            (level) => DropdownMenuItem(
                              value: level,
                              child: Text(level),
                            ),
                          )
                          .toList(),
                      onChanged: _busy
                          ? null
                          : (value) => setState(() => _level = value ?? 'B1'),
                    ),
                    const SizedBox(height: 10),
                    FilledButton.icon(
                      key: const Key('create-study-group'),
                      onPressed: _busy ? null : _create,
                      icon: const Icon(Icons.add),
                      label: const Text('Tạo nhóm'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        key: const Key('study-group-invite-code'),
                        controller: _inviteController,
                        textCapitalization: TextCapitalization.characters,
                        decoration: const InputDecoration(
                          labelText: 'Mã mời nhóm',
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    IconButton.filled(
                      key: const Key('join-study-group'),
                      onPressed: _busy ? null : _join,
                      tooltip: 'Tham gia nhóm',
                      icon: const Icon(Icons.login),
                    ),
                  ],
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            Text('Nhóm của tôi', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              key: const Key('open-global-leaderboard'),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => LeaderboardPage(apiClient: widget.apiClient),
                ),
              ),
              icon: const Icon(Icons.emoji_events_outlined),
              label: const Text('Bảng xếp hạng theo cấp độ'),
            ),
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
                  return _GroupNotice(
                    message: _errorText(snapshot.error),
                    onRetry: _refresh,
                  );
                }
                final groups = snapshot.data ?? const [];
                if (groups.isEmpty) {
                  return const _GroupNotice(
                    message: 'Bạn chưa có nhóm học tập nào.',
                  );
                }
                return Column(
                  children: groups
                      .map(
                        (group) => Card(
                          child: ListTile(
                            onTap: () => _openGroup(group),
                            leading: const CircleAvatar(
                              child: Icon(Icons.forum_outlined),
                            ),
                            title: Text(
                              group['name']?.toString() ?? 'Nhóm học tập',
                            ),
                            subtitle: Text(
                              '${group['member_count'] ?? 0} thành viên · ${group['level'] ?? 'Chưa chọn cấp độ'}',
                            ),
                            trailing: const Icon(Icons.chevron_right),
                          ),
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

class StudyGroupDetailPage extends StatefulWidget {
  const StudyGroupDetailPage({
    super.key,
    required this.apiClient,
    required this.group,
  });

  final ApiClient apiClient;
  final Map<String, dynamic> group;

  @override
  State<StudyGroupDetailPage> createState() => _StudyGroupDetailPageState();
}

class _StudyGroupDetailPageState extends State<StudyGroupDetailPage> {
  late Future<List<Map<String, dynamic>>> _future;

  String get _groupId => widget.group['id']?.toString() ?? '';

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.studyGroupAssignments(_groupId);
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.studyGroupAssignments(_groupId);
    setState(() => _future = next);
    await next;
  }

  Future<void> _createAssignment() async {
    final input = await showDialog<_AssignmentDraft>(
      context: context,
      builder: (_) => const _AssignmentDialog(),
    );
    if (input == null) return;
    try {
      await widget.apiClient.createStudyGroupAssignment(
        groupId: _groupId,
        title: input.title,
        skill: input.skill,
        content: input.content,
        estimatedMinutes: input.estimatedMinutes,
        dueAt: input.dueAt,
      );
      await _refresh();
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Đã tạo bài tập chung.')));
      }
    } on ApiException catch (exception) {
      if (mounted) _showMessage(exception.message);
    } catch (_) {
      if (mounted) _showMessage('Không thể tạo bài tập.');
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.group['name']?.toString() ?? 'Nhóm học tập';
    final code = widget.group['invite_code']?.toString();
    return Scaffold(
      appBar: AppBar(
        title: Text(name),
        actions: [
          IconButton(
            tooltip: 'Bảng xếp hạng',
            icon: const Icon(Icons.emoji_events_outlined),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => LeaderboardPage(
                  apiClient: widget.apiClient,
                  groupId: _groupId,
                ),
              ),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Card(
              color: Theme.of(context).colorScheme.primaryContainer,
              child: ListTile(
                leading: const Icon(Icons.groups_rounded),
                title: Text('${widget.group['member_count'] ?? 0} thành viên'),
                subtitle: Text(
                  code == null
                      ? 'Mời bạn bè bằng mã nhóm của người tạo.'
                      : 'Mã mời: $code',
                ),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              key: const Key('create-group-assignment'),
              onPressed: _createAssignment,
              icon: const Icon(Icons.assignment_outlined),
              label: const Text('Tạo bài tập chung'),
            ),
            const SizedBox(height: 20),
            Text(
              'Bài tập của nhóm',
              style: Theme.of(context).textTheme.titleLarge,
            ),
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
                  return _GroupNotice(
                    message: _errorText(snapshot.error),
                    onRetry: _refresh,
                  );
                }
                final assignments = snapshot.data ?? const [];
                if (assignments.isEmpty) {
                  return const _GroupNotice(
                    message: 'Chưa có bài tập. Hãy tạo bài đầu tiên.',
                  );
                }
                return Column(
                  children: assignments.map((assignment) {
                    final assignmentId = assignment['id']?.toString() ?? '';
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                assignment['title']?.toString() ?? 'Bài tập',
                              ),
                              subtitle: Text(
                                '${assignment['created_by_name'] ?? 'Thành viên'} · ${assignment['peer_review_count'] ?? 0} lượt peer review',
                              ),
                            ),
                            Wrap(
                              spacing: 8,
                              children: [
                                FilledButton.tonalIcon(
                                  key: Key(
                                    'open-group-assignment-$assignmentId',
                                  ),
                                  onPressed: () async {
                                    await Navigator.of(context).push(
                                      MaterialPageRoute<void>(
                                        builder: (_) =>
                                            AssignmentSubmissionPage(
                                              apiClient: widget.apiClient,
                                              assignment: assignment,
                                            ),
                                      ),
                                    );
                                    if (mounted) _refresh();
                                  },
                                  icon: const Icon(Icons.edit_note),
                                  label: const Text('Làm bài'),
                                ),
                                OutlinedButton.icon(
                                  key: Key('peer-review-$assignmentId'),
                                  onPressed: () => Navigator.of(context).push(
                                    MaterialPageRoute<void>(
                                      builder: (_) => PeerReviewPage(
                                        apiClient: widget.apiClient,
                                        groupId: _groupId,
                                        assignment: assignment,
                                      ),
                                    ),
                                  ),
                                  icon: const Icon(Icons.rate_review_outlined),
                                  label: const Text('Peer review'),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class PeerReviewPage extends StatefulWidget {
  const PeerReviewPage({
    super.key,
    required this.apiClient,
    required this.groupId,
    required this.assignment,
  });

  final ApiClient apiClient;
  final String groupId;
  final Map<String, dynamic> assignment;

  @override
  State<PeerReviewPage> createState() => _PeerReviewPageState();
}

class _PeerReviewPageState extends State<PeerReviewPage> {
  late Future<List<Map<String, dynamic>>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() {
    return widget.apiClient.peerReviewQueue(
      groupId: widget.groupId,
      assignmentId: widget.assignment['id']?.toString() ?? '',
    );
  }

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _future = next);
    await next;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Peer review')),
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
                padding: const EdgeInsets.all(20),
                children: [
                  _GroupNotice(
                    message: _errorText(snapshot.error),
                    onRetry: _refresh,
                  ),
                ],
              );
            }
            final targets = snapshot.data ?? const [];
            if (targets.isEmpty) {
              return ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  _GroupNotice(message: 'Chưa có bài của bạn bè cần chấm.'),
                ],
              );
            }
            return ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(
                  'Đọc kỹ bài làm và góp ý cụ thể để cùng tiến bộ.',
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 12),
                ...targets.map(
                  (target) => _PeerReviewCard(
                    apiClient: widget.apiClient,
                    target: target,
                    onSubmitted: _refresh,
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _PeerReviewCard extends StatefulWidget {
  const _PeerReviewCard({
    required this.apiClient,
    required this.target,
    required this.onSubmitted,
  });

  final ApiClient apiClient;
  final Map<String, dynamic> target;
  final Future<void> Function() onSubmitted;

  @override
  State<_PeerReviewCard> createState() => _PeerReviewCardState();
}

class _PeerReviewCardState extends State<_PeerReviewCard> {
  final _feedbackController = TextEditingController();
  double _score = 7;
  bool _busy = false;

  @override
  void dispose() {
    _feedbackController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_feedbackController.text.trim().length < 3) return;
    setState(() => _busy = true);
    try {
      await widget.apiClient.createPeerReview(
        submissionId: widget.target['submission_id']?.toString() ?? '',
        score: _score,
        feedback: _feedbackController.text,
      );
      await widget.onSubmitted();
    } on ApiException catch (exception) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(exception.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Bài của ${widget.target['author_name'] ?? 'bạn học'}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(widget.target['input_text']?.toString() ?? ''),
            const SizedBox(height: 10),
            Text('Điểm: ${_score.toStringAsFixed(1)}/10'),
            Slider(
              value: _score,
              min: 0,
              max: 10,
              divisions: 20,
              label: _score.toStringAsFixed(1),
              onChanged: _busy
                  ? null
                  : (value) => setState(() => _score = value),
            ),
            TextField(
              controller: _feedbackController,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Nhận xét',
                hintText: 'Nêu điểm tốt và một gợi ý cải thiện...',
              ),
            ),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: _busy ? null : _submit,
              icon: const Icon(Icons.check),
              label: Text(_busy ? 'Đang lưu...' : 'Gửi peer review'),
            ),
          ],
        ),
      ),
    );
  }
}

class LeaderboardPage extends StatefulWidget {
  const LeaderboardPage({super.key, required this.apiClient, this.groupId});

  final ApiClient apiClient;
  final String? groupId;

  @override
  State<LeaderboardPage> createState() => _LeaderboardPageState();
}

class _LeaderboardPageState extends State<LeaderboardPage> {
  late Future<List<Map<String, dynamic>>> _future;
  String _level = 'B1';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<List<Map<String, dynamic>>> _load() {
    if (widget.groupId == null) {
      return widget.apiClient.leaderboard(level: _level);
    }
    return widget.apiClient.studyGroupLeaderboard(
      widget.groupId!,
      level: _level,
    );
  }

  void _changeLevel(String? value) {
    if (value == null || value == _level) return;
    setState(() {
      _level = value;
      _future = _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.groupId == null
              ? 'Bảng xếp hạng theo cấp độ'
              : 'Bảng xếp hạng nhóm',
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            DropdownButtonFormField<String>(
              initialValue: _level,
              decoration: const InputDecoration(labelText: 'Cấp độ'),
              items: const ['A1', 'A2', 'B1', 'B2', 'C1']
                  .map(
                    (level) =>
                        DropdownMenuItem(value: level, child: Text(level)),
                  )
                  .toList(),
              onChanged: _changeLevel,
            ),
            const SizedBox(height: 12),
            Expanded(
              child: FutureBuilder<List<Map<String, dynamic>>>(
                future: _future,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  if (snapshot.hasError) {
                    return Center(child: Text(_errorText(snapshot.error)));
                  }
                  final entries = snapshot.data ?? const [];
                  if (entries.isEmpty) {
                    return const Center(
                      child: Text('Chưa có dữ liệu xếp hạng.'),
                    );
                  }
                  return ListView.builder(
                    itemCount: entries.length,
                    itemBuilder: (context, index) {
                      final entry = entries[index];
                      return Card(
                        child: ListTile(
                          leading: CircleAvatar(
                            child: Text('${entry['rank'] ?? index + 1}'),
                          ),
                          title: Text(
                            entry['display_name']?.toString() ?? 'Người học',
                          ),
                          subtitle: Text(
                            '${entry['level'] ?? '—'} · ${entry['submissions_count'] ?? 0} bài · ${entry['peer_reviews_count'] ?? 0} review',
                          ),
                          trailing: Text('${entry['points'] ?? 0} điểm'),
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AssignmentDraft {
  const _AssignmentDraft({
    required this.title,
    required this.skill,
    required this.content,
    required this.estimatedMinutes,
    required this.dueAt,
  });

  final String title;
  final String skill;
  final String content;
  final int estimatedMinutes;
  final DateTime dueAt;
}

class _AssignmentDialog extends StatefulWidget {
  const _AssignmentDialog();

  @override
  State<_AssignmentDialog> createState() => _AssignmentDialogState();
}

class _AssignmentDialogState extends State<_AssignmentDialog> {
  final _title = TextEditingController();
  final _content = TextEditingController();
  String _skill = 'writing';

  @override
  void dispose() {
    _title.dispose();
    _content.dispose();
    super.dispose();
  }

  void _save() {
    if (_title.text.trim().length < 2 || _content.text.trim().length < 3) {
      return;
    }
    Navigator.of(context).pop(
      _AssignmentDraft(
        title: _title.text.trim(),
        skill: _skill,
        content: _content.text.trim(),
        estimatedMinutes: 20,
        dueAt: DateTime.now().add(const Duration(days: 2)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Tạo bài tập chung'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _title,
              decoration: const InputDecoration(labelText: 'Tiêu đề'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _content,
              minLines: 3,
              maxLines: 5,
              decoration: const InputDecoration(labelText: 'Yêu cầu bài tập'),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: _skill,
              decoration: const InputDecoration(labelText: 'Kỹ năng'),
              items: const ['reading', 'writing', 'speaking']
                  .map(
                    (skill) =>
                        DropdownMenuItem(value: skill, child: Text(skill)),
                  )
                  .toList(),
              onChanged: (value) => setState(() => _skill = value ?? 'writing'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Hủy'),
        ),
        FilledButton(onPressed: _save, child: const Text('Tạo bài')),
      ],
    );
  }
}

class _GroupNotice extends StatelessWidget {
  const _GroupNotice({required this.message, this.onRetry});

  final String message;
  final Future<void> Function()? onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null)
              TextButton(onPressed: onRetry, child: const Text('Tải lại')),
          ],
        ),
      ),
    );
  }
}

String _errorText(Object? error) {
  if (error is ApiException) return error.message;
  return 'Không thể tải nhóm học tập.';
}
