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
    _future = widget.apiClient.notifications();
  }

  Future<void> _refresh() async {
    final next = widget.apiClient.notifications();
    setState(() => _future = next);
    await next;
  }

  Future<void> _markAllRead() async {
    await widget.apiClient.markAllNotificationsRead();
    await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        surfaceTintColor: Colors.transparent,
        actions: [
          IconButton(
            tooltip: 'Mark all as read',
            onPressed: _markAllRead,
            icon: const Icon(Icons.done_all),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
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
                    title: 'Could not load notifications',
                    message: snapshot.error.toString(),
                    isError: true,
                  ),
                ],
              );
            }
            final items =
                (snapshot.data?['items'] as List?)
                    ?.whereType<Map>()
                    .map((item) => item.cast<String, dynamic>())
                    .toList() ??
                const <Map<String, dynamic>>[];
            if (items.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(20),
                children: const [
                  SizedBox(height: 56),
                  _NotificationNotice(
                    icon: Icons.notifications_none_rounded,
                    title: 'You are all caught up',
                    message:
                        'Group activity and learning reminders will appear here.',
                  ),
                ],
              );
            }
            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              itemCount: items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final item = items[index];
                final read = item['read_at'] != null;
                return Card(
                  color: read
                      ? null
                      : Theme.of(context).colorScheme.primaryContainer,
                  child: ListTile(
                    leading: Icon(
                      read
                          ? Icons.notifications_none_outlined
                          : Icons.notifications_active_outlined,
                    ),
                    title: Text(item['title']?.toString() ?? 'Notification'),
                    subtitle: Text(item['body']?.toString() ?? ''),
                    trailing: read
                        ? null
                        : IconButton(
                            tooltip: 'Mark as read',
                            onPressed: () async {
                              await widget.apiClient.markNotificationRead(
                                item['id']?.toString() ?? '',
                              );
                              await _refresh();
                            },
                            icon: const Icon(Icons.done),
                          ),
                  ),
                );
              },
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
    this.isError = false,
  });

  final IconData icon;
  final String title;
  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final color = isError
        ? Theme.of(context).colorScheme.error
        : Theme.of(context).colorScheme.primary;
    return Card(
      color: color.withValues(alpha: 0.08),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color),
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
