import 'package:flutter/widgets.dart';

/// EMBEDHUNT AI spacing, radius & elevation scale (8-pt grid).
class EHSpacing {
  EHSpacing._();

  static const double xxs = 2;
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;
  static const double huge = 48;

  // Radius
  static const double radiusSm = 8;
  static const double radiusMd = 12;
  static const double radiusLg = 16;
  static const double radiusXl = 20;
  static const double radiusPill = 999;

  // Common insets
  static const EdgeInsets screen = EdgeInsets.symmetric(horizontal: 16);
  static const EdgeInsets card = EdgeInsets.all(16);
  static const EdgeInsets cardTight = EdgeInsets.all(12);

  /// Extra breathing room so content never hides behind the bottom nav.
  static const EdgeInsets scrollBottom = EdgeInsets.only(bottom: 120);
}
