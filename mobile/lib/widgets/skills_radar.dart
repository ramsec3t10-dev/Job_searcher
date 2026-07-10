import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/typography_legacy.dart';

/// A labelled radar chart for a small set of categories (0–100 each).
class SkillsRadar extends StatelessWidget {
  const SkillsRadar({
    super.key,
    required this.values,
    this.color = EHColors.brand,
    this.size = 240,
  });

  /// Ordered map of axis label → value (0–100).
  final Map<String, double> values;
  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    final labels = values.keys.toList();
    final entries = values.values
        .map((v) => RadarEntry(value: v.clamp(0, 100).toDouble()))
        .toList();

    if (labels.length < 3) {
      return const SizedBox.shrink();
    }

    return SizedBox(
      height: size,
      child: RadarChart(
        RadarChartData(
          radarShape: RadarShape.polygon,
          tickCount: 4,
          ticksTextStyle: const TextStyle(color: Colors.transparent, fontSize: 0),
          radarBorderData: BorderSide(color: context.divider, width: 1),
          gridBorderData: BorderSide(color: context.divider, width: 1),
          tickBorderData: BorderSide(color: context.divider, width: 1),
          titlePositionPercentageOffset: 0.14,
          getTitle: (index, angle) => RadarChartTitle(
            text: index < labels.length ? labels[index] : '',
          ),
          titleTextStyle: EHType.caption(context.textSecondary),
          dataSets: [
            RadarDataSet(
              dataEntries: entries,
              fillColor: color.withValues(alpha: 0.22),
              borderColor: color,
              borderWidth: 2,
              entryRadius: 3,
            ),
          ],
        ),
      ),
    );
  }
}
