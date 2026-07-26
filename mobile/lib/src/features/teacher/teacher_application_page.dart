import 'package:flutter/material.dart';

import '../../core/api_client.dart';

class TeacherApplicationPage extends StatefulWidget {
  const TeacherApplicationPage({super.key, required this.apiClient});

  final ApiClient apiClient;

  @override
  State<TeacherApplicationPage> createState() => _TeacherApplicationPageState();
}

class _TeacherApplicationPageState extends State<TeacherApplicationPage> {
  final _formKey = GlobalKey<FormState>();
  final _motivationController = TextEditingController();
  final _organizationController = TextEditingController();
  Map<String, dynamic>? _application;
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadApplication();
  }

  @override
  void dispose() {
    _motivationController.dispose();
    _organizationController.dispose();
    super.dispose();
  }

  Future<void> _loadApplication() async {
    try {
      final payload = await widget.apiClient.teacherApplication();
      if (!mounted) return;
      setState(() {
        _application = payload['application'] as Map<String, dynamic>?;
        _loading = false;
        _error = null;
      });
    } on ApiException catch (exception) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = exception.message;
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final application = await widget.apiClient.submitTeacherApplication(
        motivation: _motivationController.text,
        organization: _organizationController.text,
      );
      if (!mounted) return;
      setState(() {
        _application = application;
        _submitting = false;
      });
    } on ApiException catch (exception) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = exception.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hồ sơ giáo viên')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(
                  'Đăng ký trở thành giáo viên',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Bạn vẫn học như bình thường. Sau khi quản trị viên xem hồ sơ và duyệt, tài khoản mới có quyền tạo lớp.',
                ),
                const SizedBox(height: 16),
                if (_error != null) ...[
                  _MessageCard(message: _error!, isError: true),
                  const SizedBox(height: 12),
                ],
                if (_application?['status'] == 'pending')
                  _ApplicationStatusCard(
                    title: 'Hồ sơ đang chờ duyệt',
                    message:
                        'Quản trị viên sẽ xem kinh nghiệm và mục tiêu giảng dạy của bạn. Bạn có thể tiếp tục sử dụng các tính năng học viên trong thời gian chờ.',
                    icon: Icons.schedule_outlined,
                    color: Colors.orange,
                  )
                else if (_application?['status'] == 'approved')
                  _ApplicationStatusCard(
                    title: 'Hồ sơ đã được duyệt',
                    message:
                        'Quyền giáo viên đã được cấp. Hãy đăng nhập Teacher Dashboard trên web để quản lý lớp học.',
                    icon: Icons.verified_outlined,
                    color: Colors.green,
                  )
                else ...[
                  if (_application?['status'] == 'rejected') ...[
                    _ApplicationStatusCard(
                      title: 'Hồ sơ cần bổ sung',
                      message:
                          _application?['review_note']?.toString() ??
                          'Quản trị viên chưa thể duyệt hồ sơ lần này. Bạn có thể cập nhật và gửi lại.',
                      icon: Icons.info_outline,
                      color: Colors.red,
                    ),
                    const SizedBox(height: 16),
                  ],
                  _buildForm(),
                ],
              ],
            ),
    );
  }

  Widget _buildForm() {
    return KeyedSubtree(
      key: const Key('teacher-application-form'),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextFormField(
              key: const Key('teacher-motivation'),
              controller: _motivationController,
              minLines: 5,
              maxLines: 8,
              maxLength: 2000,
              decoration: const InputDecoration(
                labelText: 'Kinh nghiệm và lý do đăng ký',
                hintText: 'Bạn đã dạy hoặc hỗ trợ người học như thế nào?',
              ),
              validator: (value) {
                if ((value ?? '').trim().length < 20) {
                  return 'Hãy viết ít nhất 20 ký tự.';
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('teacher-organization'),
              controller: _organizationController,
              maxLength: 160,
              decoration: const InputDecoration(
                labelText: 'Đơn vị hoặc cộng đồng (không bắt buộc)',
                hintText: 'Ví dụ: trung tâm, trường học, cộng đồng…',
              ),
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              key: const Key('submit-teacher-application'),
              onPressed: _submitting ? null : _submit,
              icon: const Icon(Icons.send_outlined),
              label: Text(
                _submitting ? 'Đang gửi…' : 'Gửi hồ sơ cho quản trị viên',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ApplicationStatusCard extends StatelessWidget {
  const _ApplicationStatusCard({
    required this.title,
    required this.message,
    required this.icon,
    required this.color,
  });

  final String title;
  final String message;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: color.withValues(alpha: 0.08),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontWeight: FontWeight.bold),
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
