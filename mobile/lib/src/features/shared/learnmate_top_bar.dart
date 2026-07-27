import 'package:flutter/material.dart';

import '../../core/auth_controller.dart';

class LearnMateTopBar extends StatelessWidget implements PreferredSizeWidget {
  const LearnMateTopBar({
    super.key,
    required this.authController,
    required this.title,
    required this.onSettings,
    required this.onNotifications,
  });

  final AuthController authController;
  final String title;
  final VoidCallback onSettings;
  final VoidCallback onNotifications;

  @override
  Size get preferredSize => const Size.fromHeight(72);

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final mode = authController.activeMode == AuthController.teacherMode
        ? 'Chế độ giáo viên'
        : authController.activeLearningSpaceKind == 'class'
        ? 'Lớp · ${authController.activeLearningSpaceName}'
        : 'Tự học · ${authController.activeLearningSpaceName}';
    return AppBar(
      toolbarHeight: 72,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      leadingWidth: 64,
      leading: Padding(
        padding: const EdgeInsets.only(left: 14, top: 12, bottom: 12),
        child: IconButton.filledTonal(
          key: const Key('open-settings'),
          tooltip: 'Cài đặt',
          onPressed: onSettings,
          icon: const Icon(Icons.settings_outlined),
          style: IconButton.styleFrom(
            foregroundColor: colors.primary,
            backgroundColor: colors.primaryContainer,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
      ),
      titleSpacing: 10,
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
          ),
          Text(
            mode,
            style: Theme.of(
              context,
            ).textTheme.labelSmall?.copyWith(color: colors.onSurfaceVariant),
          ),
        ],
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 14, top: 12, bottom: 12),
          child: IconButton.filledTonal(
            key: const Key('open-notifications'),
            tooltip: 'Thông báo',
            onPressed: onNotifications,
            icon: const Icon(Icons.notifications_none_rounded),
            style: IconButton.styleFrom(
              foregroundColor: colors.onSurfaceVariant,
              backgroundColor: colors.surfaceContainerHighest,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
