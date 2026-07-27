import 'package:flutter/material.dart';

import '../../core/api_client.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.teacherApplication();
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.teacherApplication();
    setState(() => _future = next);
    await next;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Thông báo'),
        surfaceTintColor: Colors.transparent,
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  SizedBox(height: 220),
                  Center(child: CircularProgressIndicator()),
                ],
              );
            }
            if (snapshot.hasError) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20),
                children: [
                  _NotificationNotice(
                    icon: Icons.cloud_off_outlined,
                    title: 'Chưa thể tải thông báo',
                    message: snapshot.error.toString(),
                    isError: true,
                  ),
                ],
              );
            }

            final application =
                snapshot.data?['application'] as Map<String, dynamic>?;
            final status = application?['status']?.toString();
            if (status == null) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: EdgeInsets.all(20),
                children: [
                  SizedBox(height: 56),
                  _NotificationNotice(
                    icon: Icons.notifications_none_rounded,
                    title: 'Bạn đã cập nhật',
                    message:
                        'Các thông báo mới về việc học sẽ xuất hiện tại đây.',
                  ),
                ],
              );
            }
            final copy = switch (status) {
              'pending' => (
                'Hồ sơ đang chờ duyệt',
                'Quản trị viên đang xem xét hồ sơ đăng ký giáo viên của bạn.',
                Icons.schedule_outlined,
                Colors.orange,
              ),
              'approved' => (
                'Hồ sơ đã được duyệt',
                'Bạn đã có quyền teacher. Hãy chuyển sang chế độ giáo viên trong Cài đặt khi cần.',
                Icons.verified_outlined,
                Colors.green,
              ),
              _ => (
                'Hồ sơ cần bổ sung',
                application?['review_note']?.toString() ??
                    'Bạn có thể cập nhật và gửi lại hồ sơ.',
                Icons.info_outline,
                Colors.red,
              ),
            };
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              children: [
                _NotificationNotice(
                  icon: copy.$3,
                  title: copy.$1,
                  message: copy.$2,
                  color: copy.$4,
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _NotificationNotice extends StatelessWidget {
  const _NotificationNotice({
    required this.icon,
    required this.title,
    required this.message,
    this.color,
    this.isError = false,
  });

  final IconData icon;
  final String title;
  final String message;
  final Color? color;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final resolvedColor =
        color ??
        (isError
            ? Theme.of(context).colorScheme.error
            : Theme.of(context).colorScheme.primary);
    return Card(
      color: resolvedColor.withValues(alpha: 0.08),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: resolvedColor),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 6),
                  Text(message),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
