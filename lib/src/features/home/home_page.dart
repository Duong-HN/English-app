import 'package:flutter/material.dart';

import '../../core/api_client.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      _StudyPage(apiClient: widget.apiClient),
      _HistoryPage(apiClient: widget.apiClient),
      const _ProfilePage(),
    ];
    return Scaffold(
      body: SafeArea(child: pages[_selectedIndex]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) =>
            setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.school_outlined),
            label: 'Học',
          ),
          NavigationDestination(icon: Icon(Icons.history), label: 'Lịch sử'),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            label: 'Hồ sơ',
          ),
        ],
      ),
    );
  }
}

class _StudyPage extends StatefulWidget {
  const _StudyPage({required this.apiClient});

  final ApiClient apiClient;

  @override
  State<_StudyPage> createState() => _StudyPageState();
}

class _StudyPageState extends State<_StudyPage> {
  final _textController = TextEditingController(
    text: 'The quick brown fox jumps over the lazy dog.',
  );
  String _mode = 'reading';
  Map<String, dynamic>? _result;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
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
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
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
          elevation: 0,
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
                  'MVP: nhập văn bản, sau đó nhận phân tích có cấu trúc từ backend.',
                ),
                const SizedBox(height: 18),
                SegmentedButton<String>(
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
                  onSelectionChanged: (value) => setState(() {
                    _mode = value.first;
                    _result = null;
                  }),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _textController,
                  minLines: 5,
                  maxLines: 9,
                  decoration: const InputDecoration(
                    labelText: 'Nội dung tiếng Anh',
                    hintText: 'Nhập đoạn văn hoặc câu trả lời của bạn...',
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
        const SizedBox(height: 16),
        const Card(
          elevation: 0,
          child: ListTile(
            leading: CircleAvatar(child: Icon(Icons.camera_alt_outlined)),
            title: Text('OCR từ camera - bước tiếp theo'),
            subtitle: Text(
              'Chụp ảnh, trích xuất văn bản trên thiết bị rồi đưa vào cùng luồng phân tích.',
            ),
          ),
        ),
      ],
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result, required this.type});

  final Map<String, dynamic> result;
  final String type;

  @override
  Widget build(BuildContext context) {
    final vocabulary = (result['vocabulary'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>();
    final issues = (result['issues'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>();
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.check_circle, color: Colors.green),
                const SizedBox(width: 8),
                Text(
                  'Kết quả ${type == 'reading'
                      ? 'đọc hiểu'
                      : type == 'writing'
                      ? 'bài viết'
                      : 'luyện nói'}',
                  style: Theme.of(context).textTheme.titleMedium,
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
          ],
        ),
      ),
    );
  }
}

class _HistoryPage extends StatefulWidget {
  const _HistoryPage({required this.apiClient});

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

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async =>
          setState(() => _future = widget.apiClient.history()),
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
                        elevation: 0,
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
                          trailing: item['score'] == null
                              ? null
                              : Text('${item['score']}/10'),
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
  const _ProfilePage();

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Text('Hồ sơ', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 12),
      const Card(
        elevation: 0,
        child: ListTile(
          leading: CircleAvatar(child: Icon(Icons.person)),
          title: Text('Demo learner'),
          subtitle: Text('Trình độ: đang thiết lập'),
        ),
      ),
      const SizedBox(height: 12),
      const Card(
        elevation: 0,
        child: ListTile(
          leading: Icon(Icons.info_outline),
          title: Text('Chế độ phát triển'),
          subtitle: Text(
            'Ứng dụng đang dùng demo-user và Mock AI. Cấu hình auth/LLM trước khi phát hành.',
          ),
        ),
      ),
    ],
  );
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({required this.message, this.isError = false});

  final String message;
  final bool isError;

  @override
  Widget build(BuildContext context) => Card(
    elevation: 0,
    color: isError ? Colors.red.shade50 : null,
    child: Padding(padding: const EdgeInsets.all(16), child: Text(message)),
  );
}
