import 'package:flutter/material.dart';

import '../../core/auth_controller.dart';
import '../teacher/teacher_application_page.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key, required this.authController});

  final AuthController authController;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  bool _studyReminders = true;
  late Future<List<Map<String, dynamic>>> _spacesFuture;

  @override
  void initState() {
    super.initState();
    _spacesFuture = _loadSpaces();
  }

  Future<List<Map<String, dynamic>>> _loadSpaces() async {
    final spaces = await widget.authController.apiClient.learningSpaces();
    if (spaces.isNotEmpty &&
        widget.authController.activeLearningSpaceId == null) {
      final selfSpace = spaces.firstWhere(
        (space) => space['kind']?.toString() == 'self',
        orElse: () => spaces.first,
      );
      widget.authController.setActiveLearningSpace(selfSpace);
    }
    return spaces;
  }

  void _selectLearningSpace(Map<String, dynamic> space) {
    widget.authController.setActiveLearningSpace(space);
    Navigator.of(context).pop();
  }

  void _selectMode(String mode) {
    if (mode == widget.authController.activeMode) return;
    Navigator.of(context).pop();
    widget.authController.setActiveMode(mode);
  }

  Future<void> _openTeacherApplication() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            TeacherApplicationPage(apiClient: widget.authController.apiClient),
      ),
    );
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.authController.user ?? const <String, dynamic>{};
    final colors = Theme.of(context).colorScheme;
    final isTeacher = widget.authController.canUseTeacherMode;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cài đặt'),
        surfaceTintColor: Colors.transparent,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          _SectionLabel(label: 'Tài khoản'),
          Card(
            color: colors.primaryContainer.withValues(alpha: 0.55),
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: colors.primary,
                    foregroundColor: colors.onPrimary,
                    child: Text(_initials(user['display_name']?.toString())),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user['display_name']?.toString() ?? 'LearnMate',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 3),
                        Text(user['email']?.toString() ?? ''),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 22),
          _SectionLabel(label: 'Không gian học tập'),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _spacesFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Card(
                  child: Padding(
                    padding: EdgeInsets.all(18),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                );
              }
              if (snapshot.hasError) {
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.cloud_off_outlined),
                    title: const Text('Không tải được không gian học'),
                    trailing: IconButton(
                      tooltip: 'Thử lại',
                      onPressed: () => setState(() {
                        _spacesFuture = _loadSpaces();
                      }),
                      icon: const Icon(Icons.refresh),
                    ),
                  ),
                );
              }
              final spaces = snapshot.data ?? const [];
              if (spaces.isEmpty) {
                return const Card(
                  child: ListTile(
                    leading: Icon(Icons.auto_stories_outlined),
                    title: Text('Chưa có không gian học tập'),
                  ),
                );
              }
              return Column(
                children: spaces
                    .map(
                      (space) => _LearningSpaceCard(
                        space: space,
                        selected:
                            space['id']?.toString() ==
                            widget.authController.activeLearningSpaceId,
                        onTap: () => _selectLearningSpace(space),
                      ),
                    )
                    .toList(),
              );
            },
          ),
          const SizedBox(height: 22),
          _SectionLabel(label: 'Chế độ sử dụng'),
          if (isTeacher)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Một tài khoản, hai không gian',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Quyền teacher vẫn được giữ nguyên. Bạn có thể chuyển sang học như learner bất cứ lúc nào.',
                    ),
                    const SizedBox(height: 14),
                    SegmentedButton<String>(
                      key: const Key('account-mode-switch'),
                      segments: const [
                        ButtonSegment(
                          value: AuthController.learnerMode,
                          label: Text('Học viên'),
                          icon: Icon(Icons.menu_book_outlined),
                        ),
                        ButtonSegment(
                          value: AuthController.teacherMode,
                          label: Text('Giáo viên'),
                          icon: Icon(Icons.school_outlined),
                        ),
                      ],
                      selected: {widget.authController.activeMode},
                      onSelectionChanged: (selection) {
                        if (selection.isNotEmpty) _selectMode(selection.first);
                      },
                    ),
                  ],
                ),
              ),
            )
          else
            Card(
              child: ListTile(
                leading: Icon(Icons.school_outlined, color: colors.primary),
                title: const Text('Đăng ký làm giáo viên'),
                subtitle: const Text(
                  'Gửi hồ sơ để quản trị viên xem xét và cấp quyền teacher.',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: _openTeacherApplication,
                key: const Key('settings-teacher-application'),
              ),
            ),
          const SizedBox(height: 22),
          _SectionLabel(label: 'Trải nghiệm học tập'),
          Card(
            child: SwitchListTile.adaptive(
              value: _studyReminders,
              onChanged: (value) => setState(() => _studyReminders = value),
              secondary: const Icon(Icons.alarm_outlined),
              title: const Text('Nhắc lịch học'),
              subtitle: const Text(
                'Nhận nhắc nhở khi đến thời gian học mỗi ngày.',
              ),
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            key: const Key('settings-logout'),
            onPressed: widget.authController.logout,
            icon: const Icon(Icons.logout),
            label: const Text('Đăng xuất'),
          ),
        ],
      ),
    );
  }
}

class _LearningSpaceCard extends StatelessWidget {
  const _LearningSpaceCard({
    required this.space,
    required this.selected,
    required this.onTap,
  });

  final Map<String, dynamic> space;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isClass = space['kind']?.toString() == 'class';
    final level = space['current_level']?.toString();
    final course = space['course_code']?.toString();
    final metadata = <String>[
      isClass ? 'Bài giao từ giáo viên' : 'Giáo trình tự học theo level',
    ];
    if (level != null) metadata.add(level);
    if (course != null) metadata.add(course);
    return Card(
      color: selected ? Theme.of(context).colorScheme.primaryContainer : null,
      child: ListTile(
        key: ValueKey('learning-space-${space['id']}'),
        onTap: onTap,
        leading: Icon(
          isClass ? Icons.groups_outlined : Icons.auto_stories_outlined,
        ),
        title: Text(space['name']?.toString() ?? 'Không gian học tập'),
        subtitle: Text(metadata.join(' · ')),
        trailing: selected
            ? const Icon(Icons.check_circle, color: Colors.green)
            : const Icon(Icons.chevron_right),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Theme.of(context).colorScheme.primary,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.1,
        ),
      ),
    );
  }
}

String _initials(String? value) {
  final parts = (value ?? 'LM').trim().split(RegExp(r'\s+'));
  if (parts.isEmpty) return 'LM';
  if (parts.length == 1) {
    return parts.first.characters.take(2).toString().toUpperCase();
  }
  return '${parts.first.characters.first}${parts.last.characters.first}'
      .toUpperCase();
}
