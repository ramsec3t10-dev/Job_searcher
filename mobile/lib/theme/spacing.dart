// The uppercase BorderRadius getters (EHRadius.LG, …) are a deliberate
// design-system DSL mirroring the lowercase raw doubles; silence the
// naming lint for this tokens file only.
// ignore_for_file: non_constant_identifier_names

import 'package:flutter/widgets.dart';

/// EMBEDHUNT AI spacing scale (8-pt grid). Canonical v6 API.
class EHSpace {
  EHSpace._();

  static const double xxs = 2;
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;
  static const double huge = 48;

  // Common insets
  static const EdgeInsets screenPad = EdgeInsets.symmetric(horizontal: 16);
  static const EdgeInsets cardPad = EdgeInsets.all(16);
  static const EdgeInsets cardPadSM = EdgeInsets.all(12);
  static const EdgeInsets cardPadLG = EdgeInsets.all(20);

  /// Extra breathing room so content never hides behind the bottom nav.
  static const EdgeInsets scrollBottom = EdgeInsets.only(bottom: 120);
}

/// EMBEDHUNT AI corner-radius scale. Raw doubles plus ready-made
/// [BorderRadius] getters. Canonical v6 API.
class EHRadius {
  EHRadius._();

  static const double xs = 6;
  static const double sm = 10;
  static const double md = 14;
  static const double lg = 18;
  static const double xl = 24;
  static const double xxl = 32;
  static const double full = 100;

  static BorderRadius get XS => BorderRadius.circular(xs);
  static BorderRadius get SM => BorderRadius.circular(sm);
  static BorderRadius get MD => BorderRadius.circular(md);
  static BorderRadius get LG => BorderRadius.circular(lg);
  static BorderRadius get XL => BorderRadius.circular(xl);
  static BorderRadius get XXL => BorderRadius.circular(xxl);
  static BorderRadius get FULL => BorderRadius.circular(full);
}

/// Legacy spacing/radius API (pre-v6). Delegates to [EHSpace] / [EHRadius].
/// Retained so pre-refactor screens keep compiling.
class EHSpacing {
  EHSpacing._();

  static const double xxs = EHSpace.xxs;
  static const double xs = EHSpace.xs;
  static const double sm = EHSpace.sm;
  static const double md = EHSpace.md;
  static const double lg = EHSpace.lg;
  static const double xl = EHSpace.xl;
  static const double xxl = EHSpace.xxl;
  static const double xxxl = EHSpace.xxxl;
  static const double huge = EHSpace.huge;

  static const double radiusSm = 8;
  static const double radiusMd = 12;
  static const double radiusLg = 16;
  static const double radiusXl = 20;
  static const double radiusPill = 999;

  static const EdgeInsets screen = EHSpace.screenPad;
  static const EdgeInsets card = EHSpace.cardPad;
  static const EdgeInsets cardTight = EHSpace.cardPadSM;
  static const EdgeInsets scrollBottom = EHSpace.scrollBottom;
}
