class NewsArticle {
  final String title;
  final String? summary;
  final String url;
  final String source;
  final DateTime publishedAt;
  final List<String> symbols;
  final String? category;

  NewsArticle({
    required this.title,
    this.summary,
    required this.url,
    required this.source,
    required this.publishedAt,
    required this.symbols,
    this.category,
  });

  factory NewsArticle.fromJson(Map<String, dynamic> json) {
    return NewsArticle(
      title: json['title'],
      summary: json['summary'],
      url: json['url'],
      source: json['source'],
      publishedAt: DateTime.parse(json['published_at']),
      symbols: List<String>.from(json['symbols'] ?? []),
      category: json['category'],
    );
  }
}
