import 'package:flutter/material.dart';

import '../../core/auth_controller.dart';
import '../settings/notifications_page.dart';
import '../settings/settings_page.dart';
import '../shared/learnmate_top_bar.dart';

class TeacherModePage extends StatelessWidget {
  const TeacherModePage({super.key, required this.authController});

  final AuthController authController;

  Future<void> _openSettings(BuildContext context) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SettingsPage(authController: authController),
      ),
    );
  }

  Future<void> _openNotifications(BuildContext context) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => NotificationsPage(apiClient: authController.apiClient),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: LearnMateTopBar(
        authController: authController,
        title: 'Không gian giáo viên',
        onSettings: () => _openSettings(context),
        onNotifications: () => _openNotifications(context),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
          children: [
            Card(
              color: colors.secondaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.school_rounded,
                      size: 38,
                      color: colors.secondary,
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Bạn đang ở chế độ giáo viên',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Dùng Teacher Dashboard trên web để tạo lớp, giao bài và phản hồi bài làm. Dữ liệu vẫn dùng chung với tài khoản learner này.',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  const ListTile(
                    leading: Icon(Icons.groups_outlined),
                    title: Text('Quản lý lớp học'),
                    subtitle: Text(
                      'Tạo lớp và theo dõi học viên trên Teacher Dashboard.',
                    ),
                  ),
                  const Divider(height: 1),
                  const ListTile(
                    leading: Icon(Icons.rate_review_outlined),
                    title: Text('Phản hồi bài làm'),
                    subtitle: Text(
                      'Xem phân tích AI và gửi nhận xét cho học viên.',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              key: const Key('switch-to-learner-mode'),
              onPressed: () =>
                  authController.setActiveMode(AuthController.learnerMode),
              icon: const Icon(Icons.menu_book_outlined),
              label: const Text('Chuyển sang chế độ học viên'),
            ),
          ],
        ),
      ),
    );
  }
}
