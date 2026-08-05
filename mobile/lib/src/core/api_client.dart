import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client, String? baseUrl})
    : _client = client ?? http.Client(),
      baseUrl =
          baseUrl ??
          const String.fromEnvironment(
            'API_BASE_URL',
            defaultValue: 'http://10.0.2.2:8000',
          );

  final http.Client _client;
  final String baseUrl;
  String? accessToken;
  String? learningSpaceId;

  static const _timeout = Duration(seconds: 30);
  static const _analysisPollInterval = Duration(milliseconds: 500);
  static const _analysisMaxPolls = 120;
  static const _learningPathPollInterval = Duration(milliseconds: 500);
  static const _learningPathMaxPolls = 120;

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    return _post(
      '/api/v1/auth/register',
      body: {'email': email, 'password': password, 'display_name': displayName},
      authenticated: false,
    );
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    return _post(
      '/api/v1/auth/login',
      body: {'email': email, 'password': password},
      authenticated: false,
    );
  }

  Future<Map<String, dynamic>> profile() => _get('/api/v1/auth/me');

  Future<Map<String, dynamic>> analyze({
    required String type,
    required String inputText,
    String? learningPathId,
    int? taskDay,
    String? lessonId,
    void Function(String status)? onStatus,
  }) {
    return _analyzeWithJob(
      type: type,
      inputText: inputText,
      learningPathId: learningPathId,
      taskDay: taskDay,
      lessonId: lessonId,
      onStatus: onStatus,
    );
  }

  Future<Map<String, dynamic>> _analyzeWithJob({
    required String type,
    required String inputText,
    String? learningPathId,
    int? taskDay,
    String? lessonId,
    void Function(String status)? onStatus,
  }) async {
    final idempotencyKey =
        'mobile-${DateTime.now().microsecondsSinceEpoch}-$type';
    final job = await _post(
      '/api/v1/analysis-jobs/$type',
      body: {
        'input_text': inputText,
        ...?(learningPathId == null
            ? null
            : {'learning_path_id': learningPathId}),
        ...?(taskDay == null ? null : {'task_day': taskDay}),
        ...?(lessonId == null ? null : {'lesson_id': lessonId}),
      },
      extraHeaders: {'Idempotency-Key': idempotencyKey},
    );

    var current = job;
    onStatus?.call(current['status']?.toString() ?? 'queued');
    for (var attempt = 0; attempt < _analysisMaxPolls; attempt++) {
      final status = current['status']?.toString();
      if (status == 'succeeded') {
        final analysisId = current['analysis_id']?.toString();
        if (analysisId == null || analysisId.isEmpty) {
          throw const ApiException('AI job hoàn tất nhưng thiếu kết quả.');
        }
        return _get('/api/v1/analyses/${Uri.encodeComponent(analysisId)}');
      }
      if (status == 'failed') {
        onStatus?.call('failed');
        throw ApiException(
          current['error_message']?.toString() ?? 'AI không thể xử lý bài này.',
        );
      }
      if (attempt > 0) {
        await Future<void>.delayed(_analysisPollInterval);
      }
      current = await _get(
        '/api/v1/analysis-jobs/${Uri.encodeComponent(current['id'].toString())}',
      );
      onStatus?.call(current['status']?.toString() ?? 'processing');
    }
    throw const ApiException('AI xử lý quá lâu. Hãy thử lại sau.');
  }

  Future<List<Map<String, dynamic>>> history() async {
    final payload = await _get('/api/v1/analyses');
    return (payload['items'] as List<dynamic>).cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> generateLearningPath({
    required String goal,
    required String currentLevel,
    required int minutesPerDay,
    void Function(String status)? onStatus,
  }) async {
    final job = await _post(
      '/api/v1/learning-path-jobs',
      body: {
        'goal': goal,
        'current_level': currentLevel,
        'minutes_per_day': minutesPerDay,
      },
      extraHeaders: {
        'Idempotency-Key':
            'mobile-learning-path-${DateTime.now().microsecondsSinceEpoch}',
      },
    );

    return _pollLearningPathJob(job, onStatus: onStatus);
  }

  Future<Map<String, dynamic>> adaptLearningPath(
    String id, {
    void Function(String status)? onStatus,
  }) async {
    final encodedId = Uri.encodeComponent(id);
    final job = await _post(
      '/api/v1/learning-path-jobs/$encodedId/adapt',
      body: const {},
      extraHeaders: {
        'Idempotency-Key':
            'mobile-learning-path-adapt-$encodedId-${DateTime.now().microsecondsSinceEpoch}',
      },
    );
    return _pollLearningPathJob(job, onStatus: onStatus);
  }

  Future<Map<String, dynamic>> _pollLearningPathJob(
    Map<String, dynamic> job, {
    void Function(String status)? onStatus,
    bool fetchLearningPath = true,
  }) async {
    var current = job;
    onStatus?.call(current['status']?.toString() ?? 'queued');
    for (var attempt = 0; attempt < _learningPathMaxPolls; attempt++) {
      final currentStatus = current['status']?.toString();
      if (currentStatus == 'succeeded') {
        final learningPathId = current['learning_path_id']?.toString();
        if (learningPathId == null || learningPathId.isEmpty) {
          throw const ApiException(
            'Learning path job hoàn tất nhưng thiếu kết quả.',
          );
        }
        if (!fetchLearningPath) return current;
        return _get(
          '/api/v1/learning-paths/${Uri.encodeComponent(learningPathId)}',
        );
      }
      if (currentStatus == 'failed') {
        throw ApiException(
          current['error_message']?.toString() ??
              'Không thể tạo lộ trình học lúc này.',
        );
      }
      if (attempt > 0) {
        await Future<void>.delayed(_learningPathPollInterval);
      }
      current = await _get(
        '/api/v1/learning-path-jobs/${Uri.encodeComponent(current['id'].toString())}',
      );
      onStatus?.call(current['status']?.toString() ?? 'processing');
    }
    throw const ApiException('Tạo lộ trình mất quá lâu. Hãy thử lại sau.');
  }

  Future<Map<String, dynamic>> currentLearningPath() {
    return _get('/api/v1/learning-paths/current');
  }

  Future<Map<String, dynamic>> updateDailyProgress({
    required String learningPathId,
    required int day,
    required bool completed,
    String? note,
  }) {
    return _patch(
      '/api/v1/learning-paths/$learningPathId/days/$day',
      body: {
        'completed': completed,
        ...?(note == null ? null : {'note': note}),
      },
    );
  }

  Future<Map<String, dynamic>> placementTest() =>
      _get('/api/v1/placement-test');

  Future<Map<String, dynamic>> submitPlacementTest(
    Map<String, String> answers,
  ) {
    return _post('/api/v1/placement-test/submit', body: {'answers': answers});
  }

  Future<Map<String, dynamic>> latestPlacementResult() {
    return _get('/api/v1/placement-test/latest');
  }

  Future<Map<String, dynamic>> onboarding() {
    return _get('/api/v1/onboarding');
  }

  Future<Map<String, dynamic>> updateOnboardingPreferences({
    String? goal,
    int? dailyMinutes,
  }) {
    return _patch(
      '/api/v1/onboarding/preferences',
      body: {
        ...?(goal == null ? null : {'goal': goal}),
        ...?(dailyMinutes == null ? null : {'daily_minutes': dailyMinutes}),
      },
    );
  }

  Future<Map<String, dynamic>> chooseOnboardingSelfMode() {
    return _patch('/api/v1/onboarding/mode', body: const {'kind': 'self'});
  }

  Future<Map<String, dynamic>> completeOnboarding({
    void Function(String status)? onStatus,
  }) async {
    final response = await _post(
      '/api/v1/onboarding/complete',
      body: const {},
      extraHeaders: {
        'Idempotency-Key':
            'mobile-onboarding-${DateTime.now().microsecondsSinceEpoch}',
      },
    );
    if (response['operation']?.toString() != 'onboarding') return response;
    await _pollLearningPathJob(
      response,
      onStatus: onStatus,
      fetchLearningPath: false,
    );
    return _get('/api/v1/onboarding');
  }

  Future<List<Map<String, dynamic>>> learningSpaces() async {
    final payload = await _get('/api/v1/learning-spaces');
    return _mapItems(payload, const ['items', 'spaces', 'data']);
  }

  Future<Map<String, dynamic>> chooseSelfLearningSpace() {
    return _post('/api/v1/learning-spaces/self', body: const {'kind': 'self'});
  }

  Future<Map<String, dynamic>> joinLearningSpace(String inviteCode) {
    return _post(
      '/api/v1/learning-spaces/join',
      body: {'invite_code': inviteCode.trim()},
    );
  }

  Future<List<Map<String, dynamic>>> courses({
    String? kind,
    String? level,
  }) async {
    final query = <String, String>{
      ...?(kind == null ? null : {'kind': kind}),
      ...?(level == null ? null : {'level': level}),
    };
    final suffix = query.isEmpty
        ? ''
        : '?${query.entries.map((entry) => '${Uri.encodeQueryComponent(entry.key)}=${Uri.encodeQueryComponent(entry.value)}').join('&')}';
    final payload = await _get('/api/v1/content/courses$suffix');
    return _mapItems(payload, const ['items', 'courses', 'data']);
  }

  Future<Map<String, dynamic>> course(String code) {
    return _get('/api/v1/content/courses/${Uri.encodeComponent(code)}');
  }

  Future<Map<String, dynamic>> lesson(String id) {
    return _get('/api/v1/content/lessons/${Uri.encodeComponent(id)}');
  }

  Future<Map<String, dynamic>> updateLessonProgress({
    required String lessonId,
    required String status,
    double? score,
    String? note,
  }) {
    return _patch(
      '/api/v1/content/lessons/${Uri.encodeComponent(lessonId)}/progress',
      body: {
        'status': status,
        ...?(score == null ? null : {'score': score}),
        ...?(note == null ? null : {'note': note}),
      },
    );
  }

  Future<Map<String, dynamic>> updateLessonMediaProgress({
    required String lessonId,
    required String mediaId,
    required int positionSeconds,
    required bool completed,
  }) {
    return _patch(
      '/api/v1/content/lessons/${Uri.encodeComponent(lessonId)}/media-progress',
      body: {
        'media_id': mediaId,
        'position_seconds': positionSeconds,
        'completed': completed,
      },
    );
  }

  String resolveMediaUrl(String value) {
    final parsed = Uri.tryParse(value);
    if (parsed != null && parsed.hasScheme) return value;
    return '$baseUrl${value.startsWith('/') ? value : '/$value'}';
  }

  Map<String, String> mediaHeaders() {
    final headers = <String, String>{};
    if (accessToken != null) headers['Authorization'] = 'Bearer $accessToken';
    if (learningSpaceId != null && learningSpaceId!.isNotEmpty) {
      headers['X-Learning-Space-ID'] = learningSpaceId!;
    }
    return headers;
  }

  Future<Map<String, dynamic>> teacherApplication() {
    return _get('/api/v1/teacher-applications/me');
  }

  Future<Map<String, dynamic>> notifications() {
    return _get('/api/v1/notifications');
  }

  Future<Map<String, dynamic>> registerPushDevice({
    required String token,
    required String platform,
    String? appVersion,
  }) {
    return _post(
      '/api/v1/notifications/devices',
      body: {
        'token': token,
        'platform': platform,
        if (appVersion != null && appVersion.isNotEmpty)
          'app_version': appVersion,
      },
    );
  }

  Future<void> unregisterPushDevice(String token) async {
    await _post(
      '/api/v1/notifications/devices/unregister',
      body: {'token': token},
    );
  }

  Future<Map<String, dynamic>> markNotificationRead(String notificationId) {
    return _post('/api/v1/notifications/$notificationId/read', body: const {});
  }

  Future<void> markAllNotificationsRead() async {
    await _post('/api/v1/notifications/read-all', body: const {});
  }

  Future<Map<String, dynamic>> submitTeacherApplication({
    required String motivation,
    String? organization,
  }) {
    return _post(
      '/api/v1/teacher-applications',
      body: {
        'motivation': motivation.trim(),
        ...?(organization == null || organization.trim().isEmpty
            ? null
            : {'organization': organization.trim()}),
      },
    );
  }

  Future<Map<String, dynamic>> home() {
    return _get('/api/v1/home');
  }

  Future<List<Map<String, dynamic>>> classes() async {
    final payload = await _get('/api/v1/classes');
    return _mapItems(payload, const ['items', 'classes', 'data']);
  }

  Future<Map<String, dynamic>> joinClass(String inviteCode) {
    return _post(
      '/api/v1/classes/join',
      body: {'invite_code': inviteCode.trim()},
    );
  }

  Future<List<Map<String, dynamic>>> classAssignments(String classId) async {
    final payload = await _get('/api/v1/classes/$classId/assignments');
    return _mapItems(payload, const ['items', 'assignments', 'tasks', 'data']);
  }

  Future<Map<String, dynamic>> submitAssignment({
    required String assignmentId,
    required String inputText,
  }) {
    return _post(
      '/api/v1/assignments/$assignmentId/submit',
      body: {'input_text': inputText},
    );
  }

  Future<Map<String, dynamic>> assignmentSubmission(String assignmentId) {
    return _get('/api/v1/assignments/$assignmentId/submission');
  }

  Future<List<Map<String, dynamic>>> studyGroups() async {
    final payload = await _get('/api/v1/study-groups');
    return _mapItems(payload, const ['items', 'groups', 'data']);
  }

  Future<Map<String, dynamic>> createStudyGroup({
    required String name,
    String? description,
    String? level,
    int memberLimit = 8,
  }) {
    return _post(
      '/api/v1/study-groups',
      body: {
        'name': name.trim(),
        ...?(description == null || description.trim().isEmpty
            ? null
            : {'description': description.trim()}),
        ...?(level == null || level.trim().isEmpty ? null : {'level': level}),
        'member_limit': memberLimit,
      },
    );
  }

  Future<Map<String, dynamic>> joinStudyGroup(
    String inviteCode, {
    String? inviteToken,
  }) {
    return _post(
      '/api/v1/study-groups/join',
      body: {
        ...?(inviteCode.trim().isEmpty
            ? null
            : {'invite_code': inviteCode.trim()}),
        ...?(inviteToken == null || inviteToken.trim().isEmpty
            ? null
            : {'invite_token': inviteToken.trim()}),
      },
    );
  }

  Future<Map<String, dynamic>> studyGroupInvitePreview(String token) {
    return _get(
      '/api/v1/study-groups/invite-preview/${Uri.encodeComponent(token)}',
    );
  }

  Future<List<Map<String, dynamic>>> studyGroupInvitations() async {
    final payload = await _get('/api/v1/study-groups/invitations');
    return _mapItems(payload, const ['items', 'data']);
  }

  Future<Map<String, dynamic>> approveStudyGroupInvitation(
    String invitationId,
  ) {
    return _post(
      '/api/v1/study-groups/invitations/$invitationId/approve',
      body: const {},
    );
  }

  Future<Map<String, dynamic>> declineStudyGroupInvitation(
    String invitationId,
  ) {
    return _post(
      '/api/v1/study-groups/invitations/$invitationId/decline',
      body: const {},
    );
  }

  Future<List<Map<String, dynamic>>> studyGroupAssignments(
    String groupId,
  ) async {
    final payload = await _get('/api/v1/study-groups/$groupId/assignments');
    return _mapItems(payload, const ['items', 'assignments', 'data']);
  }

  Future<Map<String, dynamic>> createStudyGroupAssignment({
    required String groupId,
    required String title,
    required String skill,
    required String content,
    required int estimatedMinutes,
    required DateTime dueAt,
    DateTime? reviewDeadline,
    int reviewersPerSubmission = 1,
    Map<String, dynamic>? rubric,
  }) {
    return _post(
      '/api/v1/study-groups/$groupId/assignments',
      body: {
        'title': title.trim(),
        'skill': skill,
        'content': content.trim(),
        'estimated_minutes': estimatedMinutes,
        'due_at': dueAt.toUtc().toIso8601String(),
        ...?(reviewDeadline == null
            ? null
            : {'review_deadline': reviewDeadline.toUtc().toIso8601String()}),
        ...?(reviewersPerSubmission == 1
            ? null
            : {'reviewers_per_submission': reviewersPerSubmission}),
        ...?(rubric == null ? null : {'rubric': rubric}),
      },
    );
  }

  Future<List<Map<String, dynamic>>> peerReviewQueue({
    required String groupId,
    required String assignmentId,
  }) async {
    final payload = await _get(
      '/api/v1/study-groups/$groupId/assignments/$assignmentId/peer-reviews',
    );
    return _mapItems(payload, const ['items', 'data']);
  }

  Future<Map<String, dynamic>> createPeerReview({
    required String submissionId,
    double? score,
    required String feedback,
    Map<String, double>? rubricScores,
  }) {
    return _post(
      '/api/v1/submissions/$submissionId/peer-reviews',
      body: {
        ...?(score == null ? null : {'score': score}),
        'feedback': feedback.trim(),
        ...?(rubricScores == null ? null : {'rubric_scores': rubricScores}),
      },
    );
  }

  Future<List<Map<String, dynamic>>> studyGroupLeaderboard(
    String groupId, {
    String? level,
  }) async {
    final suffix = level == null || level.isEmpty
        ? ''
        : '?level=${Uri.encodeQueryComponent(level)}';
    final payload = await _get(
      '/api/v1/study-groups/$groupId/leaderboard$suffix',
    );
    return _mapItems(payload, const ['items', 'data']);
  }

  Future<List<Map<String, dynamic>>> leaderboard({String? level}) async {
    final suffix = level == null || level.isEmpty
        ? ''
        : '?level=${Uri.encodeQueryComponent(level)}';
    final payload = await _get('/api/v1/leaderboards$suffix');
    return _mapItems(payload, const ['items', 'data']);
  }

  Future<Map<String, dynamic>> lookupWord(String word) {
    final encodedWord = Uri.encodeComponent(word.trim());
    return _get('/api/v1/vocabulary/lookup/$encodedWord');
  }

  Future<void> deleteAnalysis(String id) async {
    final response = await _client
        .delete(Uri.parse('$baseUrl/api/v1/analyses/$id'), headers: _headers())
        .timeout(_timeout);
    _decodeSuccess(response);
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _client
        .get(Uri.parse('$baseUrl$path'), headers: _headers())
        .timeout(_timeout);
    return _decodeSuccess(response);
  }

  Future<Map<String, dynamic>> _patch(
    String path, {
    required Map<String, dynamic> body,
  }) async {
    final response = await _client
        .patch(
          Uri.parse('$baseUrl$path'),
          headers: _headers(),
          body: jsonEncode(body),
        )
        .timeout(_timeout);
    return _decodeSuccess(response);
  }

  Future<Map<String, dynamic>> _post(
    String path, {
    required Map<String, dynamic> body,
    bool authenticated = true,
    Map<String, String>? extraHeaders,
  }) async {
    final response = await _client
        .post(
          Uri.parse('$baseUrl$path'),
          headers: {
            ..._headers(authenticated: authenticated),
            ...?extraHeaders,
          },
          body: jsonEncode(body),
        )
        .timeout(_timeout);
    return _decodeSuccess(response);
  }

  Map<String, String> _headers({bool authenticated = true}) {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (authenticated && accessToken != null) {
      headers['Authorization'] = 'Bearer $accessToken';
    }
    if (learningSpaceId != null && learningSpaceId!.isNotEmpty) {
      headers['X-Learning-Space-ID'] = learningSpaceId!;
    }
    return headers;
  }

  Map<String, dynamic> _decodeSuccess(http.Response response) {
    final payload = _decode(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _errorMessage(payload),
        statusCode: response.statusCode,
      );
    }
    return payload;
  }

  Map<String, dynamic> _decode(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) return decoded;
      if (decoded is List<dynamic>) return {'items': decoded};
      return {'detail': 'Invalid server response (${response.statusCode})'};
    } catch (_) {
      return {'detail': 'Invalid server response (${response.statusCode})'};
    }
  }

  List<Map<String, dynamic>> _mapItems(
    Map<String, dynamic> payload,
    List<String> keys,
  ) {
    for (final key in keys) {
      final value = payload[key];
      if (value is List) {
        return value.whereType<Map<String, dynamic>>().toList();
      }
      if (value is Map<String, dynamic>) {
        for (final nestedKey in keys) {
          final nested = value[nestedKey];
          if (nested is List) {
            return nested.whereType<Map<String, dynamic>>().toList();
          }
        }
      }
    }
    return const [];
  }

  String _errorMessage(Map<String, dynamic> payload) {
    final detail = payload['detail'];
    if (detail is String) return detail;
    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is Map<String, dynamic>) {
        return first['msg']?.toString() ?? 'Invalid request';
      }
    }
    return 'Request failed';
  }

  void close() => _client.close();
}
