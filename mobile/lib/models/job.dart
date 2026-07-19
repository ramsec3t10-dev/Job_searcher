/// A ranked job recommendation, mirrors the API's serialized job.
class Job {
  final int rank;
  final String jobId;
  final String title;
  final String company;
  final String companyTier;
  final String location;
  final String sourcePortal;
  final String? applyUrl;
  final double? salaryMinLpa;
  final double? salaryMaxLpa;
  final bool meetsSalary;
  final int matchScore;
  final String matchTier;
  final bool isAutoApply;
  final List<String> matchedSkills;
  final List<String> missingSkills;
  final String explanation;
  final String recommendation;
  final String? domainCode;
  final String? domainName;

  const Job({
    required this.rank,
    required this.jobId,
    required this.title,
    required this.company,
    required this.companyTier,
    required this.location,
    required this.sourcePortal,
    required this.applyUrl,
    required this.salaryMinLpa,
    required this.salaryMaxLpa,
    required this.meetsSalary,
    required this.matchScore,
    required this.matchTier,
    required this.isAutoApply,
    required this.matchedSkills,
    required this.missingSkills,
    required this.explanation,
    required this.recommendation,
    this.domainCode,
    this.domainName,
  });

  static List<String> _stringList(dynamic value) {
    if (value is List) return value.map((e) => e.toString()).toList();
    return const [];
  }

  static double? _toDouble(dynamic value) {
    if (value == null) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }

  factory Job.fromJson(Map<String, dynamic> json) {
    return Job(
      rank: json['rank'] as int? ?? 0,
      jobId: json['job_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      company: json['company'] as String? ?? '',
      companyTier: json['company_tier'] as String? ?? 'other',
      location: json['location'] as String? ?? '',
      sourcePortal: json['source_portal'] as String? ?? '',
      applyUrl: json['apply_url'] as String?,
      salaryMinLpa: _toDouble(json['salary_min_lpa']),
      salaryMaxLpa: _toDouble(json['salary_max_lpa']),
      meetsSalary: json['meets_salary'] as bool? ?? false,
      matchScore: json['match_score'] as int? ?? 0,
      matchTier: json['match_tier'] as String? ?? 'partial',
      isAutoApply: json['is_auto_apply'] as bool? ?? false,
      matchedSkills: _stringList(json['matched_skills']),
      missingSkills: _stringList(json['missing_skills']),
      explanation: json['explanation'] as String? ?? '',
      recommendation: json['recommendation'] as String? ?? '',
      domainCode: json['domain_code'] as String?,
      domainName: json['domain_name'] as String?,
    );
  }

  String get salaryLabel {
    if (salaryMinLpa == null && salaryMaxLpa == null) return 'Not disclosed';
    final min = salaryMinLpa?.toStringAsFixed(0) ?? '?';
    final max = salaryMaxLpa?.toStringAsFixed(0) ?? '?';
    return '$min–$max LPA';
  }
}
