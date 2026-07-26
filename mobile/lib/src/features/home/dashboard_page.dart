import 'package:flutter/material.dart';

import '../../core/api_client.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({
    super.key,
    required this.apiClient,
    required this.displayName,
    required this.onOpenLearningPath,
    required this.onOpenClasses,
    required this.onOpenStudy,
  });

  final ApiClient apiClient;
  final String displayName;
  final VoidCallback onOpenLearningPath;
  final VoidCallback onOpenClasses;
  final ValueChanged<Map<String, dynamic>?> onOpenStudy;

  @override
  State<DashboardPage> createState() => DashboardPageState();
}

class DashboardPageState extends State<DashboardPage> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.apiClient.home();
  }

  Future<void> refresh() async {
    final next = widget.apiClient.home();
    setState(() {
      _future = next;
    });
    await next;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: refresh,
      child: ListView(
        key: const Key('home-dashboard'),
        padding: const EdgeInsets.fromLTRB(20, 24, 20, 32),
        children: [
          Text(
            'Xin chào, ${_shortName(widget.displayName)} 👋',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          const Text('Lộ trình cá nhân và bài từ lớp trong cùng một ngày học.'),
          const SizedBox(height: 18),
          FutureBuilder<Map<String, dynamic>>(
            future: _future,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (snapshot.hasError) {
                return _DashboardNotice(
                  message: snapshot.error is ApiException
                      ? (snapshot.error! as ApiException).message
                      : 'Không thể tải kế hoạch hôm nay.',
                  actionLabel: 'Thử lại',
                  onAction: refresh,
                  error: true,
                );
              }
              return _DashboardContent(
                payload: snapshot.data ?? const {},
                onOpenLearningPath: widget.onOpenLearningPath,
                onOpenClasses: widget.onOpenClasses,
                onOpenStudy: widget.onOpenStudy,
              );
            },
          ),
        ],
      ),
    );
  }
}

class _DashboardContent extends StatelessWidget {
  const _DashboardContent({
    required this.payload,
    required this.onOpenLearningPath,
    required this.onOpenClasses,
    required this.onOpenStudy,
  });

  final Map<String, dynamic> payload;
  final VoidCallback onOpenLearningPath;
  final VoidCallback onOpenClasses;
  final ValueChanged<Map<String, dynamic>?> onOpenStudy;

  @override
  Widget build(BuildContext context) {
    final today = _asMap(payload['today']) ?? const <String, dynamic>{};
    final path =
        _asMap(
          payload['learning_path'] ??
              payload['current_learning_path'] ??
              payload['personal_learning_path'] ??
              payload['personal_path'],
        ) ??
        const <String, dynamic>{};
    final plan = _asMap(path['plan']) ?? const <String, dynamic>{};
    final listedPersonalTasks = _firstList(
      [today, payload, plan],
      const ['personal_tasks', 'learning_path_tasks', 'daily_tasks'],
    );
    final nextPersonalTask = _firstMap(
      [today, payload],
      const ['next_personal_task', 'personal_task'],
    );
    final personalTasks = listedPersonalTasks.isNotEmpty
        ? listedPersonalTasks
        : [?nextPersonalTask];
    final classTasks = _firstList(
      [today, payload],
      const [
        'class_tasks',
        'class_assignments',
        'assignments',
        'teacher_tasks',
      ],
    );
    final outstandingClassTasks = classTasks
        .where((task) => !_isCompletedTask(task))
        .toList();
    final dailyMinutes =
        _firstInt(
          [today, payload, path],
          const ['daily_minutes', 'daily_budget_minutes', 'minutes_per_day'],
        ) ??
        30;
    final plannedMinutes =
        _firstInt(
          [today, payload],
          const ['planned_minutes', 'total_planned_minutes', 'used_minutes'],
        ) ??
        _taskMinutes([...classTasks, ...personalTasks]);
    final level = _firstText(
      [path, payload],
      const ['current_level', 'level', 'placement_level'],
    );
    final goal = _firstText([path, payload], const ['goal', 'primary_goal']);
    final progress = dailyMinutes <= 0
        ? 0.0
        : (plannedMinutes / dailyMinutes).clamp(0.0, 1.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          color: Theme.of(context).colorScheme.primaryContainer,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.today_outlined),
                    const SizedBox(width: 8),
                    Text(
                      'Kế hoạch hôm nay',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const Spacer(),
                    Text('$dailyMinutes phút'),
                  ],
                ),
                const SizedBox(height: 12),
                LinearProgressIndicator(value: progress),
                const SizedBox(height: 8),
                Text(
                  plannedMinutes == 0
                      ? 'Chưa có nhiệm vụ được lên lịch.'
                      : '$plannedMinutes phút đã được lên kế hoạch từ lộ trình và lớp học.',
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  key: const Key('continue-learning'),
                  onPressed: outstandingClassTasks.isNotEmpty
                      ? onOpenClasses
                      : () => onOpenStudy(nextPersonalTask),
                  icon: Icon(
                    outstandingClassTasks.isNotEmpty
                        ? Icons.assignment_outlined
                        : Icons.play_arrow,
                  ),
                  label: Text(
                    outstandingClassTasks.isNotEmpty
                        ? 'Làm bài từ lớp'
                        : 'Tiếp tục học',
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.route_outlined),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Lộ trình của tôi',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    if (level != null) Chip(label: Text(level)),
                  ],
                ),
                if (goal != null) ...[const SizedBox(height: 8), Text(goal)],
                const SizedBox(height: 12),
                if (personalTasks.isEmpty)
                  const Text('Lộ trình chưa có nhiệm vụ cho hôm nay.')
                else
                  ...personalTasks
                      .take(2)
                      .map(
                        (task) => _TaskTile(
                          task: task,
                          fromClass: false,
                          onTap: () => onOpenStudy(task),
                        ),
                      ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    key: const Key('open-learning-path'),
                    onPressed: onOpenLearningPath,
                    icon: const Icon(Icons.arrow_forward),
                    label: const Text('Xem toàn bộ lộ trình'),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.groups_outlined),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Bài từ lớp',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    if (classTasks.isNotEmpty)
                      Badge(label: Text('${classTasks.length}')),
                  ],
                ),
                const SizedBox(height: 10),
                if (classTasks.isEmpty)
                  const Text('Không có bài tập lớp đang chờ.')
                else
                  ...classTasks
                      .take(3)
                      .map(
                        (task) => _TaskTile(
                          task: task,
                          fromClass: true,
                          onTap: onOpenClasses,
                        ),
                      ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                    key: const Key('open-classes'),
                    onPressed: onOpenClasses,
                    icon: const Icon(Icons.arrow_forward),
                    label: const Text('Mở lớp học'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _TaskTile extends StatelessWidget {
  const _TaskTile({
    required this.task,
    required this.fromClass,
    required this.onTap,
  });

  final Map<String, dynamic> task;
  final bool fromClass;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final nested = _asMap(task['assignment'] ?? task['task']);
    final source = nested == null ? task : {...task, ...nested};
    final title = _firstText([source], const ['title', 'name']) ?? 'Nhiệm vụ';
    final skill = _firstText([source], const ['skill', 'type']);
    final minutes = _firstInt(
      [source],
      const ['estimated_minutes', 'duration_minutes', 'minutes'],
    );
    final due = _firstText([source], const ['due_at', 'deadline']);
    final status = _firstText([source], const ['submission_status', 'status']);
    final completed = const {
      'submitted',
      'reviewed',
      'completed',
    }.contains(status?.toLowerCase());
    return ListTile(
      onTap: onTap,
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        child: Icon(
          completed
              ? Icons.check
              : fromClass
              ? Icons.assignment_outlined
              : Icons.auto_awesome,
        ),
      ),
      title: Text(title),
      subtitle: Text(
        [
          if (skill != null) _skillLabel(skill),
          if (minutes != null) '$minutes phút',
          if (due != null) 'Hạn ${_shortDate(due)}',
          if (completed) status == 'reviewed' ? 'Đã nhận xét' : 'Đã nộp',
        ].join(' · '),
      ),
      trailing: const Icon(Icons.chevron_right),
    );
  }
}

bool _isCompletedTask(Map<String, dynamic> task) {
  final nested = _asMap(task['assignment'] ?? task['task']);
  final source = nested == null ? task : {...task, ...nested};
  final status = _firstText([source], const ['submission_status', 'status']);
  return const {
    'submitted',
    'reviewed',
    'completed',
  }.contains(status?.toLowerCase());
}

class _DashboardNotice extends StatelessWidget {
  const _DashboardNotice({
    required this.message,
    this.actionLabel,
    this.onAction,
    this.error = false,
  });

  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final bool error;

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

List<Map<String, dynamic>> _firstList(
  List<Map<String, dynamic>> sources,
  List<String> keys,
) {
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value is List) {
        return value.map(_asMap).whereType<Map<String, dynamic>>().toList();
      }
    }
  }
  return const [];
}

Map<String, dynamic>? _firstMap(
  List<Map<String, dynamic>> sources,
  List<String> keys,
) {
  for (final source in sources) {
    for (final key in keys) {
      final value = _asMap(source[key]);
      if (value != null) return value;
    }
  }
  return null;
}

String? _firstText(List<Map<String, dynamic>> sources, List<String> keys) {
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value == null || value is Map || value is List) continue;
      final text = value.toString().trim();
      if (text.isNotEmpty) return text;
    }
  }
  return null;
}

int? _firstInt(List<Map<String, dynamic>> sources, List<String> keys) {
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value is int) return value;
      final parsed = int.tryParse(value?.toString() ?? '');
      if (parsed != null) return parsed;
    }
  }
  return null;
}

int _taskMinutes(List<Map<String, dynamic>> tasks) {
  return tasks.fold(0, (total, task) {
    final nested = _asMap(task['assignment'] ?? task['task']);
    return total +
        (_firstInt(
              [?nested, task],
              const ['estimated_minutes', 'duration_minutes', 'minutes'],
            ) ??
            0);
  });
}

String _shortName(String value) {
  final parts = value.trim().split(RegExp(r'\s+'));
  return parts.isEmpty || parts.first.isEmpty ? 'bạn' : parts.last;
}

String _shortDate(String value) {
  final parsed = DateTime.tryParse(value)?.toLocal();
  if (parsed == null) return value;
  String two(int number) => number.toString().padLeft(2, '0');
  return '${two(parsed.day)}/${two(parsed.month)}';
}

String _skillLabel(String value) => switch (value.toLowerCase()) {
  'reading' => 'Đọc',
  'writing' => 'Viết',
  'speaking' => 'Nói',
  'listening' => 'Nghe',
  _ => value,
};
