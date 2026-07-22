import 'package:flutter/material.dart';

import '../../core/api_client.dart';

class ClassesPage extends StatefulWidget {
  const ClassesPage({
    super.key,
    required this.apiClient,
    required this.isLearner,
  });

  final ApiClient apiClient;
  final bool isLearner;

  @override
  State<ClassesPage> createState() => ClassesPageState();
}

class ClassesPageState extends State<ClassesPage> {
  final _joinFormKey = GlobalKey<FormState>();
  final _joinCodeController = TextEditingController();
  final _leavingClassIds = <String>{};
  final _submittingAssignmentIds = <String>{};

  List<Map<String, dynamic>> _classes = const [];
  List<Map<String, dynamic>> _assignments = const [];
  String? _selectedClassId;
  String? _classesError;
  String? _joinError;
  String? _assignmentsError;
  bool _loadingClasses = false;
  bool _loadingAssignments = false;
  bool _joining = false;
  int _classesRequest = 0;
  int _assignmentsRequest = 0;

  List<Map<String, dynamic>> get _pendingClasses =>
      _classes.where((item) => _membershipStatus(item) == 'pending').toList();

  List<Map<String, dynamic>> get _activeClasses => _classes
      .where(
        (item) => _membershipStatus(item) == 'active' && _classIsActive(item),
      )
      .toList();

  List<Map<String, dynamic>> get _pausedClasses => _classes
      .where(
        (item) => _membershipStatus(item) == 'active' && !_classIsActive(item),
      )
      .toList();

  Map<String, dynamic>? get _selectedClass {
    for (final item in _activeClasses) {
      if (_itemId(item) == _selectedClassId) return item;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    if (widget.isLearner) refresh();
  }

  @override
  void dispose() {
    _joinCodeController.dispose();
    super.dispose();
  }

  Future<void> refresh() async {
    if (!widget.isLearner) return;
    final request = ++_classesRequest;
    setState(() {
      _loadingClasses = true;
      _classesError = null;
    });
    try {
      final classes = await widget.apiClient.myClasses();
      if (!mounted || request != _classesRequest) return;
      final activeIds = classes
          .where(
            (item) =>
                _membershipStatus(item) == 'active' && _classIsActive(item),
          )
          .map(_itemId)
          .where((id) => id.isNotEmpty)
          .toList();
      final selectedId = activeIds.contains(_selectedClassId)
          ? _selectedClassId
          : activeIds.firstOrNull;
      setState(() {
        _classes = classes;
        _selectedClassId = selectedId;
        if (selectedId == null) {
          _assignments = const [];
          _assignmentsError = null;
          _loadingAssignments = false;
          _assignmentsRequest++;
        }
      });
      if (selectedId != null) await _loadAssignments(selectedId);
    } on ApiException catch (exception) {
      if (mounted && request == _classesRequest) {
        setState(() => _classesError = exception.message);
      }
    } catch (_) {
      if (mounted && request == _classesRequest) {
        setState(() => _classesError = 'Không thể tải danh sách lớp học.');
      }
    } finally {
      if (mounted && request == _classesRequest) {
        setState(() => _loadingClasses = false);
      }
    }
  }

  Future<void> _joinClass() async {
    if (_joining || _joinFormKey.currentState?.validate() != true) return;
    final code = _joinCodeController.text.trim().toUpperCase();
    _joinCodeController.value = TextEditingValue(
      text: code,
      selection: TextSelection.collapsed(offset: code.length),
    );
    setState(() {
      _joining = true;
      _joinError = null;
    });
    try {
      final joinedClass = await widget.apiClient.joinClass(code);
      if (!mounted) return;
      _joinCodeController.clear();
      final pending = _membershipStatus(joinedClass) == 'pending';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            pending ? 'Đã gửi yêu cầu tham gia lớp.' : 'Đã tham gia lớp học.',
          ),
        ),
      );
      await refresh();
    } on ApiException catch (exception) {
      if (mounted) setState(() => _joinError = exception.message);
    } catch (_) {
      if (mounted) {
        setState(() => _joinError = 'Không thể gửi yêu cầu tham gia lớp.');
      }
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  Future<void> _selectClass(Map<String, dynamic> classroom) async {
    final classId = _itemId(classroom);
    if (classId.isEmpty) return;
    setState(() => _selectedClassId = classId);
    await _loadAssignments(classId);
  }

  Future<void> _loadAssignments(String classId) async {
    final request = ++_assignmentsRequest;
    setState(() {
      _loadingAssignments = true;
      _assignmentsError = null;
    });
    try {
      final assignments = await widget.apiClient.classAssignments(classId);
      if (!mounted ||
          request != _assignmentsRequest ||
          classId != _selectedClassId) {
        return;
      }
      setState(() => _assignments = assignments);
    } on ApiException catch (exception) {
      if (mounted && request == _assignmentsRequest) {
        setState(() => _assignmentsError = exception.message);
      }
    } catch (_) {
      if (mounted && request == _assignmentsRequest) {
        setState(() => _assignmentsError = 'Không thể tải bài tập của lớp.');
      }
    } finally {
      if (mounted && request == _assignmentsRequest) {
        setState(() => _loadingAssignments = false);
      }
    }
  }

  Future<void> _leaveClass(Map<String, dynamic> classroom) async {
    final classId = _itemId(classroom);
    if (classId.isEmpty || _leavingClassIds.contains(classId)) return;
    final pending = _membershipStatus(classroom) == 'pending';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(pending ? 'Hủy yêu cầu tham gia?' : 'Rời lớp học?'),
        content: Text(
          pending
              ? 'Yêu cầu đang chờ duyệt sẽ bị hủy.'
              : 'Bạn sẽ không còn xem được bài tập của lớp này.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Giữ lại'),
          ),
          FilledButton(
            key: const Key('confirm-leave-class'),
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(pending ? 'Hủy yêu cầu' : 'Rời lớp'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _leavingClassIds.add(classId));
    try {
      await widget.apiClient.leaveClass(classId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            pending ? 'Đã hủy yêu cầu tham gia.' : 'Đã rời lớp học.',
          ),
        ),
      );
      await refresh();
    } on ApiException catch (exception) {
      if (mounted) _showErrorSnackBar(exception.message);
    } catch (_) {
      if (mounted) _showErrorSnackBar('Không thể cập nhật thành viên lớp.');
    } finally {
      if (mounted) setState(() => _leavingClassIds.remove(classId));
    }
  }

  Future<void> _submitAssignment(Map<String, dynamic> assignment) async {
    final assignmentId = _itemId(assignment);
    final skill = assignment['skill_type']?.toString().toLowerCase() ?? '';
    if (assignmentId.isEmpty ||
        skill.isEmpty ||
        _submittingAssignmentIds.contains(assignmentId)) {
      return;
    }
    setState(() => _submittingAssignmentIds.add(assignmentId));
    try {
      final history = await widget.apiClient.history();
      if (!mounted) return;
      final matches = history
          .where(
            (item) =>
                _itemId(item).isNotEmpty &&
                item['type']?.toString().toLowerCase() == skill,
          )
          .toList();
      if (matches.isEmpty) {
        await _showNoMatchingAnalysis(skill);
        return;
      }
      final selected = await _chooseAnalysis(matches, skill);
      if (!mounted || selected == null) return;
      await widget.apiClient.submitAssignment(
        assignmentId: assignmentId,
        analysisId: _itemId(selected),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Đã nộp bài. Bạn vẫn có thể nộp thêm lần khác.'),
        ),
      );
      final classId = assignment['class_id']?.toString() ?? _selectedClassId;
      if (classId != null && classId.isNotEmpty) {
        await _loadAssignments(classId);
      }
    } on ApiException catch (exception) {
      if (mounted) _showErrorSnackBar(exception.message);
    } catch (_) {
      if (mounted) _showErrorSnackBar('Không thể nộp bài tập.');
    } finally {
      if (mounted) {
        setState(() => _submittingAssignmentIds.remove(assignmentId));
      }
    }
  }

  Future<void> _showNoMatchingAnalysis(String skill) {
    return showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Chưa có bài phân tích phù hợp'),
        content: Text(
          'Hãy vào tab Học, hoàn thành một bài ${_skillLabel(skill).toLowerCase()} '
          'rồi quay lại nộp bài tập này.',
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Đã hiểu'),
          ),
        ],
      ),
    );
  }

  Future<Map<String, dynamic>?> _chooseAnalysis(
    List<Map<String, dynamic>> analyses,
    String skill,
  ) {
    return showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(sheetContext).height * 0.72,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 10),
              Center(
                child: Container(
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Theme.of(sheetContext).colorScheme.outlineVariant,
                    borderRadius: BorderRadius.circular(99),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 18, 20, 4),
                child: Text(
                  'Chọn bài ${_skillLabel(skill).toLowerCase()} để nộp',
                  style: Theme.of(sheetContext).textTheme.titleLarge,
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 0, 20, 12),
                child: Text(
                  'Chỉ các bài phân tích gần đây đúng kỹ năng được hiển thị.',
                ),
              ),
              const Divider(height: 1),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: analyses.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 6),
                  itemBuilder: (context, index) {
                    final analysis = analyses[index];
                    final analysisId = _itemId(analysis);
                    final input = analysis['input_text']?.toString().trim();
                    final score = analysis['score'];
                    final createdAt = _formatDate(analysis['created_at']);
                    final details = <String>[
                      if (score != null) 'Điểm $score/10',
                      if (createdAt.isNotEmpty) createdAt,
                    ].join(' · ');
                    return Card(
                      child: ListTile(
                        key: ValueKey('analysis-choice-$analysisId'),
                        leading: const Icon(Icons.description_outlined),
                        title: Text(
                          input?.isNotEmpty == true ? input! : 'Bài phân tích',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: details.isEmpty ? null : Text(details),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => Navigator.pop(sheetContext, analysis),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isLearner) return const _LearnerOnlyClassesView();
    final pending = _pendingClasses;
    final active = _activeClasses;
    final paused = _pausedClasses;
    final selectedClass = _selectedClass;
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        key: const Key('classes-page'),
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
        children: [
          Text('Lớp học', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          const Text(
            'Tham gia lớp bằng mã giáo viên cung cấp và nộp các bài đã phân tích.',
          ),
          const SizedBox(height: 18),
          _buildJoinCard(),
          if (_classesError != null) ...[
            const SizedBox(height: 14),
            _ClassMessageCard(message: _classesError!, isError: true),
          ],
          if (_loadingClasses && _classes.isEmpty) ...[
            const SizedBox(height: 24),
            const Center(child: CircularProgressIndicator()),
          ] else ...[
            if (_classes.isEmpty && _classesError == null) ...[
              const SizedBox(height: 14),
              const _ClassMessageCard(
                message: 'Bạn chưa tham gia lớp nào. Nhập mã lớp để bắt đầu.',
              ),
            ],
            if (pending.isNotEmpty) ...[
              const SizedBox(height: 20),
              _SectionTitle(title: 'Đang chờ duyệt', count: pending.length),
              const SizedBox(height: 8),
              ...pending.map(
                (item) => _ClassSummaryCard(
                  key: ValueKey('pending-class-${_itemId(item)}'),
                  classroom: item,
                  selected: false,
                  leaving: _leavingClassIds.contains(_itemId(item)),
                  onOpen: null,
                  onLeave: () => _leaveClass(item),
                ),
              ),
            ],
            if (active.isNotEmpty) ...[
              const SizedBox(height: 20),
              _SectionTitle(title: 'Lớp đang học', count: active.length),
              const SizedBox(height: 8),
              ...active.map(
                (item) => _ClassSummaryCard(
                  key: ValueKey('active-class-${_itemId(item)}'),
                  classroom: item,
                  selected: _itemId(item) == _selectedClassId,
                  leaving: _leavingClassIds.contains(_itemId(item)),
                  onOpen: () => _selectClass(item),
                  onLeave: () => _leaveClass(item),
                ),
              ),
            ],
            if (paused.isNotEmpty) ...[
              const SizedBox(height: 20),
              _SectionTitle(title: 'Lớp tạm dừng', count: paused.length),
              const SizedBox(height: 8),
              ...paused.map(
                (item) => _ClassSummaryCard(
                  key: ValueKey('paused-class-${_itemId(item)}'),
                  classroom: item,
                  selected: false,
                  leaving: _leavingClassIds.contains(_itemId(item)),
                  onOpen: null,
                  onLeave: () => _leaveClass(item),
                ),
              ),
            ],
            if (_classes.isNotEmpty &&
                pending.isEmpty &&
                active.isEmpty &&
                paused.isEmpty) ...[
              const SizedBox(height: 14),
              const _ClassMessageCard(
                message: 'Chưa có lớp đang chờ hoặc đang hoạt động.',
              ),
            ],
          ],
          if (_loadingClasses && _classes.isNotEmpty) ...[
            const SizedBox(height: 12),
            const LinearProgressIndicator(),
          ],
          if (selectedClass != null) ...[
            const SizedBox(height: 22),
            _buildClassDetail(selectedClass),
          ],
        ],
      ),
    );
  }

  Widget _buildJoinCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Form(
          key: _joinFormKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Tham gia lớp mới',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              TextFormField(
                key: const Key('class-join-code'),
                controller: _joinCodeController,
                textCapitalization: TextCapitalization.characters,
                autocorrect: false,
                enabled: !_joining,
                decoration: const InputDecoration(
                  labelText: 'Mã tham gia',
                  hintText: 'Ví dụ: ABC123',
                  prefixIcon: Icon(Icons.key_outlined),
                ),
                validator: (value) {
                  final length = value?.trim().length ?? 0;
                  if (length == 0) return 'Hãy nhập mã tham gia lớp';
                  if (length < 6 || length > 16) {
                    return 'Mã tham gia phải có từ 6 đến 16 ký tự';
                  }
                  return null;
                },
                onFieldSubmitted: (_) {
                  if (!_joining) _joinClass();
                },
              ),
              if (_joinError != null) ...[
                const SizedBox(height: 10),
                Text(
                  _joinError!,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
              const SizedBox(height: 12),
              FilledButton.icon(
                key: const Key('join-class'),
                onPressed: _joining ? null : _joinClass,
                icon: _joining
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.group_add_outlined),
                label: Text(_joining ? 'Đang gửi yêu cầu...' : 'Tham gia lớp'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildClassDetail(Map<String, dynamic> classroom) {
    final className = _className(classroom);
    return Card(
      key: const Key('selected-class-detail'),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(className, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              _teacherText(classroom),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Text('Bài tập', style: Theme.of(context).textTheme.titleMedium),
                const Spacer(),
                IconButton(
                  tooltip: 'Tải lại bài tập',
                  onPressed: _loadingAssignments
                      ? null
                      : () => _loadAssignments(_itemId(classroom)),
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            if (_loadingAssignments) const LinearProgressIndicator(),
            if (_assignmentsError != null) ...[
              const SizedBox(height: 10),
              _ClassMessageCard(message: _assignmentsError!, isError: true),
            ] else if (!_loadingAssignments && _assignments.isEmpty) ...[
              const SizedBox(height: 10),
              const _ClassMessageCard(
                message: 'Giáo viên chưa giao bài tập nào cho lớp này.',
              ),
            ] else ...[
              const SizedBox(height: 8),
              ..._assignments.map(
                (assignment) => _AssignmentCard(
                  key: ValueKey('assignment-${_itemId(assignment)}'),
                  assignment: assignment,
                  submitting: _submittingAssignmentIds.contains(
                    _itemId(assignment),
                  ),
                  onSubmit: () => _submitAssignment(assignment),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LearnerOnlyClassesView extends StatelessWidget {
  const _LearnerOnlyClassesView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const Key('classes-learner-only'),
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
      children: [
        Text('Lớp học', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 18),
        const Card(
          child: Padding(
            padding: EdgeInsets.all(20),
            child: Column(
              children: [
                Icon(Icons.school_outlined, size: 44),
                SizedBox(height: 12),
                Text(
                  'Khu vực dành cho học viên',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                ),
                SizedBox(height: 8),
                Text(
                  'Tài khoản hiện tại không thể tham gia hoặc quản lý lớp '
                  'trong ứng dụng học viên.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.count});

  final String title;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(title, style: Theme.of(context).textTheme.titleMedium),
        ),
        Badge(label: Text('$count')),
      ],
    );
  }
}

class _ClassSummaryCard extends StatelessWidget {
  const _ClassSummaryCard({
    super.key,
    required this.classroom,
    required this.selected,
    required this.leaving,
    required this.onOpen,
    required this.onLeave,
  });

  final Map<String, dynamic> classroom;
  final bool selected;
  final bool leaving;
  final VoidCallback? onOpen;
  final VoidCallback onLeave;

  @override
  Widget build(BuildContext context) {
    final membershipStatus = _membershipStatus(classroom);
    final status = membershipStatus == 'active' && !_classIsActive(classroom)
        ? 'paused'
        : membershipStatus;
    final description = classroom['description']?.toString().trim();
    final targetLevel = classroom['target_level']?.toString().trim();
    return Card(
      color: selected ? Theme.of(context).colorScheme.secondaryContainer : null,
      child: InkWell(
        onTap: onOpen,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(child: Icon(Icons.groups_outlined)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _className(classroom),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _teacherText(classroom),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  _StatusChip(status: status),
                ],
              ),
              if (description?.isNotEmpty == true) ...[
                const SizedBox(height: 10),
                Text(description!),
              ],
              if (targetLevel?.isNotEmpty == true) ...[
                const SizedBox(height: 8),
                Text(
                  'Trình độ mục tiêu: $targetLevel',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (onOpen != null)
                    TextButton.icon(
                      onPressed: onOpen,
                      icon: const Icon(Icons.assignment_outlined),
                      label: Text(selected ? 'Đang xem' : 'Xem bài tập'),
                    ),
                  const SizedBox(width: 6),
                  OutlinedButton.icon(
                    key: ValueKey(
                      status == 'pending'
                          ? 'cancel-membership-${_itemId(classroom)}'
                          : 'leave-class-${_itemId(classroom)}',
                    ),
                    onPressed: leaving ? null : onLeave,
                    icon: leaving
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(
                            status == 'pending'
                                ? Icons.close
                                : Icons.exit_to_app,
                          ),
                    label: Text(
                      status == 'pending' ? 'Hủy yêu cầu' : 'Rời lớp',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AssignmentCard extends StatelessWidget {
  const _AssignmentCard({
    super.key,
    required this.assignment,
    required this.submitting,
    required this.onSubmit,
  });

  final Map<String, dynamic> assignment;
  final bool submitting;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final skill = assignment['skill_type']?.toString().toLowerCase() ?? '';
    final instructions = assignment['instructions']?.toString().trim();
    final targetLevel = assignment['target_level']?.toString().trim();
    final dueAt = _formatDate(assignment['due_at']);
    final status = assignment['status']?.toString().toLowerCase() ?? '';
    final attempts = assignment['my_submission_count'];
    final isClosed = status == 'closed';
    final isPastDue = _isPastDue(assignment['due_at']);
    final canSubmit = !submitting && !isClosed && !isPastDue;
    final submitLabel = submitting
        ? 'Đang xử lý...'
        : isClosed
        ? 'Bài đã đóng'
        : isPastDue
        ? 'Đã quá hạn'
        : 'Chọn bài để nộp';
    return Card.outlined(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(_skillIcon(skill)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    assignment['title']?.toString() ?? 'Bài tập',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                _StatusChip(status: status, assignment: true),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                Chip(label: Text(_skillLabel(skill))),
                if (targetLevel?.isNotEmpty == true)
                  Chip(label: Text('Mức $targetLevel')),
              ],
            ),
            if (instructions?.isNotEmpty == true) ...[
              const SizedBox(height: 8),
              Text(instructions!),
            ],
            if (dueAt.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                'Hạn nộp: $dueAt',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (attempts is num && attempts > 0) ...[
              const SizedBox(height: 6),
              Text(
                'Bạn đã nộp ${attempts.toInt()} lần.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 12),
            FilledButton.tonalIcon(
              key: ValueKey('submit-assignment-${_itemId(assignment)}'),
              onPressed: canSubmit ? onSubmit : null,
              icon: submitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Icon(
                      isClosed
                          ? Icons.lock_outline
                          : isPastDue
                          ? Icons.event_busy_outlined
                          : Icons.upload_file_outlined,
                    ),
              label: Text(submitLabel),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status, this.assignment = false});

  final String status;
  final bool assignment;

  @override
  Widget build(BuildContext context) {
    final label = assignment
        ? _assignmentStatusLabel(status)
        : _membershipStatusLabel(status);
    final colorScheme = Theme.of(context).colorScheme;
    final attention =
        status == 'pending' || status == 'draft' || status == 'paused';
    return Chip(
      visualDensity: VisualDensity.compact,
      avatar: Icon(
        status == 'paused'
            ? Icons.pause_circle_outline
            : attention
            ? Icons.schedule
            : Icons.check_circle_outline,
        size: 17,
      ),
      label: Text(label),
      backgroundColor: attention
          ? colorScheme.tertiaryContainer
          : colorScheme.primaryContainer,
    );
  }
}

class _ClassMessageCard extends StatelessWidget {
  const _ClassMessageCard({required this.message, this.isError = false});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: isError ? Theme.of(context).colorScheme.errorContainer : null,
      child: Padding(padding: const EdgeInsets.all(16), child: Text(message)),
    );
  }
}

String _itemId(Map<String, dynamic> item) => item['id']?.toString() ?? '';

String _membershipStatus(Map<String, dynamic> classroom) =>
    classroom['membership_status']?.toString().toLowerCase() ?? '';

String _className(Map<String, dynamic> classroom) =>
    classroom['name']?.toString().trim().isNotEmpty == true
    ? classroom['name'].toString()
    : 'Lớp học';

bool _classIsActive(Map<String, dynamic> classroom) =>
    classroom['is_active'] != false;

String _teacherText(Map<String, dynamic> classroom) {
  final name = classroom['teacher_display_name']?.toString().trim();
  final email = classroom['teacher_email']?.toString().trim();
  if (name?.isNotEmpty == true && email?.isNotEmpty == true) {
    return 'Giáo viên: $name · $email';
  }
  if (name?.isNotEmpty == true) return 'Giáo viên: $name';
  if (email?.isNotEmpty == true) return 'Giáo viên: $email';
  return 'Giáo viên chưa cập nhật thông tin';
}

String _membershipStatusLabel(String status) {
  return switch (status) {
    'pending' => 'Đang chờ duyệt',
    'active' => 'Đang học',
    'paused' => 'Tạm dừng',
    _ => 'Chưa xác định',
  };
}

String _assignmentStatusLabel(String status) {
  return switch (status) {
    'published' => 'Đang giao',
    'open' => 'Đang mở',
    'closed' => 'Đã đóng',
    'draft' => 'Bản nháp',
    _ => status.isEmpty ? 'Chưa xác định' : status,
  };
}

String _skillLabel(String skill) {
  return switch (skill) {
    'reading' => 'Đọc hiểu',
    'writing' => 'Viết',
    'speaking' => 'Nói',
    _ => 'Kỹ năng',
  };
}

IconData _skillIcon(String skill) {
  return switch (skill) {
    'reading' => Icons.menu_book_outlined,
    'writing' => Icons.edit_outlined,
    'speaking' => Icons.mic_none,
    _ => Icons.school_outlined,
  };
}

String _formatDate(Object? value) {
  final raw = value?.toString();
  if (raw == null || raw.isEmpty) return '';
  final parsed = DateTime.tryParse(raw);
  if (parsed == null) return raw;
  final local = parsed.toLocal();
  String twoDigits(int number) => number.toString().padLeft(2, '0');
  return '${twoDigits(local.day)}/${twoDigits(local.month)}/${local.year} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}

bool _isPastDue(Object? value) {
  final raw = value?.toString();
  if (raw == null || raw.isEmpty) return false;
  final dueAt = DateTime.tryParse(raw);
  return dueAt != null && dueAt.isBefore(DateTime.now());
}
