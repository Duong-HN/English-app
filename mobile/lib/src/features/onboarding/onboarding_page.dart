import 'package:flutter/material.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({
    super.key,
    required this.apiClient,
    required this.authController,
    required this.onCompleted,
  });

  final ApiClient apiClient;
  final AuthController authController;
  final VoidCallback onCompleted;

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  Map<String, dynamic>? _onboarding;
  Map<String, dynamic>? _placementResult;
  List<Map<String, dynamic>> _questions = const [];
  final Map<String, String> _answers = {};
  final _inviteController = TextEditingController();
  int _questionIndex = 0;
  bool _loading = true;
  bool _saving = false;
  String _completionStatus = 'idle';
  String? _error;

  String get _status => _onboarding?['status']?.toString() ?? 'needs_goal';

  @override
  void dispose() {
    _inviteController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final onboarding = await widget.apiClient.onboarding();
      if (!mounted) return;
      _applyOnboarding(onboarding);
      if (_status == 'completed') {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) widget.onCompleted();
        });
        return;
      }
      if (_status == 'needs_placement') {
        final test = await widget.apiClient.placementTest();
        if (!mounted) return;
        setState(() {
          _questions = _asMaps(test['questions']);
          _questionIndex = 0;
        });
      }
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Không thể tải thông tin bắt đầu học.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _applyOnboarding(Map<String, dynamic> value) {
    final placement = _asMap(
      value['placement_result'] ?? value['placement'] ?? value['result'],
    );
    setState(() {
      _onboarding = value;
      if (placement != null) _placementResult = placement;
    });
    final space = _asMap(value['space']);
    if (space != null && value['status'] != 'needs_mode') {
      widget.authController.setActiveLearningSpace(space);
    }
  }

  Future<void> _chooseSelfMode() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final response = await widget.apiClient.chooseOnboardingSelfMode();
      if (!mounted) return;
      _applyOnboarding(response);
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể chọn không gian tự học.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _joinClass() async {
    final code = _inviteController.text.trim();
    if (code.length < 6) {
      setState(() => _error = 'Mã mời cần có ít nhất 6 ký tự.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final space = await widget.apiClient.joinLearningSpace(code);
      if (!mounted) return;
      widget.authController.setActiveLearningSpace(space);
      final onboarding = await widget.apiClient.onboarding();
      if (!mounted) return;
      _applyOnboarding(onboarding);
      widget.onCompleted();
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể tham gia lớp học.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _saveGoal(String goal) async {
    await _savePreference(() {
      return widget.apiClient.updateOnboardingPreferences(goal: goal);
    });
  }

  Future<void> _saveMinutes(int minutes) async {
    await _savePreference(() {
      return widget.apiClient.updateOnboardingPreferences(
        dailyMinutes: minutes,
      );
    });
  }

  Future<void> _savePreference(
    Future<Map<String, dynamic>> Function() request,
  ) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      var response = await request();
      if (response['status'] == null) {
        response = await widget.apiClient.onboarding();
      }
      if (!mounted) return;
      _applyOnboarding(response);
      if (_status == 'needs_placement' && _questions.isEmpty) {
        final test = await widget.apiClient.placementTest();
        if (!mounted) return;
        setState(() {
          _questions = _asMaps(test['questions']);
          _questionIndex = 0;
        });
      }
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể lưu lựa chọn.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _submitPlacement() async {
    if (_questions.isEmpty || _answers.length != _questions.length) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final result = await widget.apiClient.submitPlacementTest(_answers);
      Map<String, dynamic>? refreshed;
      try {
        refreshed = await widget.apiClient.onboarding();
      } catch (_) {
        // The scored result is enough to let the learner continue locally.
      }
      if (!mounted) return;
      setState(() {
        _placementResult = result;
        _onboarding = {
          ...?_onboarding,
          ...?refreshed,
          'status': refreshed?['status'] ?? 'needs_learning_path',
          'placement_result': refreshed?['placement_result'] ?? result,
        };
      });
    } on ApiException catch (exception) {
      if (mounted) setState(() => _error = exception.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Không thể chấm bài kiểm tra.');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _complete() async {
    setState(() {
      _saving = true;
      _error = null;
      _completionStatus = 'processing';
    });
    try {
      final response = await widget.apiClient.completeOnboarding(
        onStatus: (status) {
          if (mounted) setState(() => _completionStatus = status);
        },
      );
      if (!mounted) return;
      _applyOnboarding(response);
      setState(() => _completionStatus = 'succeeded');
      widget.onCompleted();
    } on ApiException catch (exception) {
      if (mounted) {
        setState(() {
          _completionStatus = 'failed';
          _error = exception.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _completionStatus = 'failed';
          _error = 'Chưa thể tạo lộ trình. Hãy thử lại.';
        });
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Thiết lập hành trình'),
        actions: [
          IconButton(
            tooltip: 'Đăng xuất',
            onPressed: _saving ? null : widget.authController.logout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null && _onboarding == null
            ? _LoadError(message: _error!, onRetry: _load)
            : Column(
                children: [
                  _OnboardingProgress(status: _status),
                  Expanded(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 220),
                      child: _buildStep(),
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _buildStep() {
    final error = _error;
    switch (_status) {
      case 'needs_goal':
        return _GoalStep(
          key: const ValueKey('goal-step'),
          selected: _onboarding?['goal']?.toString(),
          saving: _saving,
          error: error,
          onSelected: _saveGoal,
        );
      case 'needs_mode':
        return _ModeStep(
          key: const ValueKey('mode-step'),
          saving: _saving,
          error: error,
          inviteController: _inviteController,
          onSelfStudy: _chooseSelfMode,
          onJoinClass: _joinClass,
        );
      case 'needs_daily_time':
        return _MinutesStep(
          key: const ValueKey('minutes-step'),
          selected: _toInt(_onboarding?['daily_minutes']),
          saving: _saving,
          error: error,
          onSelected: _saveMinutes,
        );
      case 'needs_placement':
        if (_questions.isEmpty) {
          if (_saving) {
            return const Center(
              key: ValueKey('placement-loading'),
              child: CircularProgressIndicator(),
            );
          }
          return _LoadError(
            key: const ValueKey('placement-load-error'),
            message: error ?? 'Không tìm thấy câu hỏi kiểm tra.',
            onRetry: _load,
          );
        }
        final question = _questions[_questionIndex];
        final id = question['id'].toString();
        return _PlacementStep(
          key: ValueKey('placement-question-$id'),
          question: question,
          index: _questionIndex,
          total: _questions.length,
          selected: _answers[id],
          saving: _saving,
          error: error,
          onSelected: (answer) => setState(() => _answers[id] = answer),
          onBack: _questionIndex == 0
              ? null
              : () => setState(() => _questionIndex--),
          onNext: _answers[id] == null
              ? null
              : () {
                  if (_questionIndex == _questions.length - 1) {
                    _submitPlacement();
                  } else {
                    setState(() => _questionIndex++);
                  }
                },
        );
      case 'needs_learning_path':
        return _ResultStep(
          key: const ValueKey('result-step'),
          result: _placementResult ?? const {},
          saving: _saving,
          status: _completionStatus,
          error: error,
          onGenerate: _complete,
        );
      case 'completed':
        return const Center(child: CircularProgressIndicator());
      default:
        return _LoadError(
          key: const ValueKey('unknown-status'),
          message: error ?? 'Trạng thái thiết lập chưa được hỗ trợ: $_status',
          onRetry: _load,
        );
    }
  }
}

class _OnboardingProgress extends StatelessWidget {
  const _OnboardingProgress({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final current = switch (status) {
      'needs_mode' => 0,
      'needs_goal' => 1,
      'needs_daily_time' => 2,
      'needs_placement' => 3,
      _ => 4,
    };
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 8),
      child: Column(
        children: [
          LinearProgressIndicator(value: (current + 1) / 4),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              for (var index = 0; index < 5; index++)
                Text(
                  [
                    'Không gian',
                    'Mục tiêu',
                    'Thời gian',
                    'Kiểm tra',
                    'Sẵn sàng',
                  ][index],
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: index <= current
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.outline,
                    fontWeight: index == current ? FontWeight.bold : null,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ModeStep extends StatelessWidget {
  const _ModeStep({
    super.key,
    required this.saving,
    required this.error,
    required this.inviteController,
    required this.onSelfStudy,
    required this.onJoinClass,
  });

  final bool saving;
  final String? error;
  final TextEditingController inviteController;
  final VoidCallback onSelfStudy;
  final VoidCallback onJoinClass;

  @override
  Widget build(BuildContext context) {
    return _StepLayout(
      title: 'Bạn muốn học theo cách nào?',
      subtitle:
          'Bạn có thể đổi giữa Tự học và các lớp đã tham gia trong Cài đặt.',
      error: error,
      child: Column(
        children: [
          Card(
            color: Theme.of(context).colorScheme.primaryContainer,
            child: ListTile(
              key: const Key('mode-self-study'),
              enabled: !saving,
              onTap: onSelfStudy,
              leading: const Icon(Icons.auto_awesome_outlined),
              title: const Text('Tự học theo hệ thống'),
              subtitle: const Text(
                'Lộ trình theo level, mục tiêu và tiến độ riêng của bạn.',
              ),
              trailing: const Icon(Icons.chevron_right),
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.groups_outlined),
                    title: Text('Tham gia lớp học có sẵn'),
                    subtitle: Text('Nhập mã mời giáo viên gửi cho bạn.'),
                  ),
                  TextField(
                    key: const Key('onboarding-class-invite'),
                    controller: inviteController,
                    enabled: !saving,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(
                      labelText: 'Mã mời lớp',
                      hintText: 'Ví dụ: IELTS01',
                      prefixIcon: Icon(Icons.vpn_key_outlined),
                    ),
                  ),
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    key: const Key('onboarding-join-class'),
                    onPressed: saving ? null : onJoinClass,
                    icon: const Icon(Icons.group_add_outlined),
                    label: Text(saving ? 'Đang tham gia...' : 'Tham gia lớp'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GoalStep extends StatelessWidget {
  const _GoalStep({
    super.key,
    required this.selected,
    required this.saving,
    required this.error,
    required this.onSelected,
  });

  final String? selected;
  final bool saving;
  final String? error;
  final ValueChanged<String> onSelected;

  static const goals = [
    (
      'ielts',
      'IELTS',
      'Luyện các kỹ năng theo mục tiêu band',
      Icons.workspace_premium_outlined,
    ),
    (
      'communication',
      'Giao tiếp',
      'Tự tin nghe và nói trong đời sống',
      Icons.forum_outlined,
    ),
    (
      'study_abroad',
      'Du học',
      'Sẵn sàng cho học tập ở môi trường quốc tế',
      Icons.flight_takeoff_outlined,
    ),
    (
      'work',
      'Công việc',
      'Email, họp và phỏng vấn bằng tiếng Anh',
      Icons.work_outline,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return _StepLayout(
      title: 'Mục tiêu của bạn?',
      subtitle: 'Chọn một mục tiêu chính. Bạn có thể thay đổi sau.',
      error: error,
      child: Column(
        children: goals
            .map(
              (goal) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Card(
                  color: selected == goal.$1
                      ? Theme.of(context).colorScheme.primaryContainer
                      : null,
                  child: ListTile(
                    key: Key('goal-${goal.$1}'),
                    enabled: !saving,
                    onTap: () => onSelected(goal.$1),
                    leading: Icon(goal.$4),
                    title: Text(goal.$2),
                    subtitle: Text(goal.$3),
                    trailing: saving && selected == goal.$1
                        ? const SizedBox.square(
                            dimension: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.chevron_right),
                  ),
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

class _MinutesStep extends StatelessWidget {
  const _MinutesStep({
    super.key,
    required this.selected,
    required this.saving,
    required this.error,
    required this.onSelected,
  });

  final int? selected;
  final bool saving;
  final String? error;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    const values = [15, 20, 30, 45, 60];
    return _StepLayout(
      title: 'Bạn có bao nhiêu phút mỗi ngày?',
      subtitle: 'Một nhịp học đều đặn quan trọng hơn một buổi học thật dài.',
      error: error,
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        alignment: WrapAlignment.center,
        children: values
            .map(
              (minutes) => SizedBox(
                width: 132,
                height: 96,
                child: Card(
                  color: selected == minutes
                      ? Theme.of(context).colorScheme.primaryContainer
                      : null,
                  child: InkWell(
                    key: Key('minutes-$minutes'),
                    borderRadius: BorderRadius.circular(12),
                    onTap: saving ? null : () => onSelected(minutes),
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '$minutes',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const Text('phút / ngày'),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            )
            .toList(),
      ),
    );
  }
}

class _PlacementStep extends StatelessWidget {
  const _PlacementStep({
    super.key,
    required this.question,
    required this.index,
    required this.total,
    required this.selected,
    required this.saving,
    required this.error,
    required this.onSelected,
    required this.onBack,
    required this.onNext,
  });

  final Map<String, dynamic> question;
  final int index;
  final int total;
  final String? selected;
  final bool saving;
  final String? error;
  final ValueChanged<String> onSelected;
  final VoidCallback? onBack;
  final VoidCallback? onNext;

  @override
  Widget build(BuildContext context) {
    final options = _questionOptions(question);
    return _StepLayout(
      title: 'Placement Test 20 câu',
      subtitle:
          'Câu ${index + 1}/$total${question['skill'] == null ? '' : ' · ${question['skill']}'}',
      error: error,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            question['prompt']?.toString() ?? '',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 18),
          RadioGroup<String>(
            groupValue: selected,
            onChanged: saving
                ? (_) {}
                : (value) {
                    if (value != null) onSelected(value);
                  },
            child: Column(
              children: options
                  .map(
                    (option) => Card(
                      child: RadioListTile<String>(
                        key: Key('answer-${question['id']}-${option.value}'),
                        value: option.value,
                        title: Text(option.label),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: saving ? null : onBack,
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Quay lại'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  key: const Key('placement-next'),
                  onPressed: saving ? null : onNext,
                  icon: saving
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          index == total - 1
                              ? Icons.fact_check_outlined
                              : Icons.arrow_forward,
                        ),
                  label: Text(index == total - 1 ? 'Nộp bài' : 'Tiếp tục'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Kết quả chỉ ước lượng trình độ đầu vào, không phải chứng chỉ IELTS hay CEFR chính thức.',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _ResultStep extends StatelessWidget {
  const _ResultStep({
    super.key,
    required this.result,
    required this.saving,
    required this.status,
    required this.error,
    required this.onGenerate,
  });

  final Map<String, dynamic> result;
  final bool saving;
  final String status;
  final String? error;
  final VoidCallback onGenerate;

  @override
  Widget build(BuildContext context) {
    final score = result['score'] ?? 0;
    final total = result['total_questions'] ?? 20;
    final level = result['level']?.toString() ?? 'Đang cập nhật';
    final skills = _asMap(result['skill_scores']) ?? const {};
    return _StepLayout(
      title: 'Bạn đã hoàn thành!',
      subtitle: 'Đây là điểm bắt đầu để LearnMate cá nhân hóa việc học.',
      error: error,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            color: Theme.of(context).colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const Icon(Icons.emoji_events_outlined, size: 52),
                  const SizedBox(height: 10),
                  Text(level, style: Theme.of(context).textTheme.displaySmall),
                  Text('$score/$total câu đúng'),
                ],
              ),
            ),
          ),
          if (skills.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Điểm theo kỹ năng',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: skills.entries
                  .map(
                    (entry) => Chip(
                      label: Text(
                        '${_skillLabel(entry.key)}: ${_skillScore(entry.value)}',
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
          if (status != 'idle') ...[
            const SizedBox(height: 16),
            _OnboardingJobStatusCard(
              status: status,
              onRetry: status == 'failed' && !saving ? onGenerate : null,
            ),
          ],
          const SizedBox(height: 20),
          FilledButton.icon(
            key: const Key('generate-onboarding-path'),
            onPressed: saving ? null : onGenerate,
            icon: saving
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.auto_awesome),
            label: Text(
              saving ? 'Đang tạo lộ trình...' : 'Tạo lộ trình của tôi',
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Nếu việc tạo lộ trình bị gián đoạn, bạn có thể thử lại mà không cần làm lại bài kiểm tra.',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _OnboardingJobStatusCard extends StatelessWidget {
  const _OnboardingJobStatusCard({required this.status, this.onRetry});

  final String status;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final label = switch (status) {
      'succeeded' => 'Thành công',
      'failed' => 'Thất bại',
      _ => 'Đang xử lý',
    };
    final icon = switch (status) {
      'succeeded' => Icons.check_circle,
      'failed' => Icons.error_outline,
      _ => Icons.hourglass_top,
    };
    final color = switch (status) {
      'succeeded' => Colors.green,
      'failed' => Colors.red,
      _ => Colors.orange,
    };
    return Semantics(
      liveRegion: true,
      label: 'Trạng thái tạo lộ trình: $label',
      child: Card(
        key: const Key('onboarding-job-status'),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(color: color, fontWeight: FontWeight.w600),
                ),
              ),
              if (onRetry != null)
                TextButton(onPressed: onRetry, child: const Text('Thử lại')),
            ],
          ),
        ),
      ),
    );
  }
}

class _StepLayout extends StatelessWidget {
  const _StepLayout({
    required this.title,
    required this.subtitle,
    required this.child,
    this.error,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 40),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 620),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(title, style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 6),
              Text(subtitle, style: Theme.of(context).textTheme.bodyLarge),
              if (error != null) ...[
                const SizedBox(height: 12),
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(error!),
                  ),
                ),
              ],
              const SizedBox(height: 24),
              child,
            ],
          ),
        ),
      ),
    );
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({super.key, required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 52),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Thử lại'),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuestionOption {
  const _QuestionOption(this.value, this.label);

  final String value;
  final String label;
}

List<_QuestionOption> _questionOptions(Map<String, dynamic> question) {
  final raw = question['options'];
  if (raw is! List) return const [];
  return raw.asMap().entries.map((entry) {
    final item = entry.value;
    if (item is Map<String, dynamic>) {
      return _QuestionOption(
        (item['value'] ?? item['id'] ?? item['key'] ?? _letter(entry.key))
            .toString(),
        (item['label'] ?? item['text'] ?? item['title'] ?? '').toString(),
      );
    }
    return _QuestionOption(_letter(entry.key), item.toString());
  }).toList();
}

String _letter(int index) => String.fromCharCode(97 + index);

Map<String, dynamic>? _asMap(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) {
    return value.map((key, item) => MapEntry(key.toString(), item));
  }
  return null;
}

List<Map<String, dynamic>> _asMaps(Object? value) {
  if (value is! List) return const [];
  return value.map(_asMap).whereType<Map<String, dynamic>>().toList();
}

int? _toInt(Object? value) {
  if (value is int) return value;
  return int.tryParse(value?.toString() ?? '');
}

String _skillLabel(Object value) => switch (value.toString().toLowerCase()) {
  'grammar' => 'Ngữ pháp',
  'vocabulary' => 'Từ vựng',
  'reading' => 'Đọc hiểu',
  'listening' => 'Nghe',
  'speaking' => 'Nói',
  'writing' => 'Viết',
  _ => value.toString(),
};

String _skillScore(Object? value) {
  final score = _asMap(value);
  if (score == null) return value?.toString() ?? '0';
  final correct = score['correct'] ?? score['score'];
  final total = score['total'] ?? score['total_questions'];
  if (correct != null && total != null) return '$correct/$total';
  if (score['percentage'] != null) return '${score['percentage']}%';
  return score.values.join('/');
}
