class AppConfig {
  const AppConfig._();

  /// URL of the web portal used by approved teachers and administrators.
  ///
  /// Keep this value environment-specific. The default is useful for local
  /// browser development only; Android/iOS devices should receive a LAN URL
  /// through `--dart-define`.
  static const teacherDashboardUrl = String.fromEnvironment(
    'TEACHER_DASHBOARD_URL',
    defaultValue: 'http://localhost:3000',
  );

  static Uri? get teacherDashboardUri =>
      parseTeacherDashboardUrl(teacherDashboardUrl);

  static Uri? parseTeacherDashboardUrl(String rawUrl) {
    final value = rawUrl.trim();
    if (value.isEmpty) {
      return null;
    }

    final uri = Uri.tryParse(value);
    if (uri == null || uri.host.isEmpty) {
      return null;
    }

    if (uri.scheme != 'http' && uri.scheme != 'https') {
      return null;
    }

    return uri;
  }
}
