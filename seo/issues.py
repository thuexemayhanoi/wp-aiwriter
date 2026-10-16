"""Issue catalogue and factory.

Verification levels:
- VERIFIED: a deterministic rule measured it on live data (status code, missing tag, ...).
- NEEDS_REVIEW: a heuristic signal; a human must judge intent or quality before any fix.
- INFO: context or a suggestion, not a defect.
- BLOCKED: the check could not run (no credentials / no data); nothing is inferred.
"""
from dataclasses import dataclass, field, asdict

PRIORITY_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
RISK_ORDER = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
VERIFICATION_ORDER = {'VERIFIED': 0, 'NEEDS_REVIEW': 1, 'INFO': 2, 'BLOCKED': 3}

# code: (priority, verification, risk, issue text, suggested fix)
CATALOG = {
    # --- Phase 0 / inventory -----------------------------------------------------------------
    'T-LEDGER-MISSING': ('P0', 'VERIFIED', 'HIGH', 'Bài đã VERIFIED trong ledger nhưng không còn trong REST công khai',
                         'Chủ sở hữu kiểm tra bài (nháp, riêng tư, Thùng rác). KHÔNG tạo lại bài; quyết định khôi phục thủ công.'),
    'T-INVENTORY-REMOVED': ('P0', 'NEEDS_REVIEW', 'HIGH', 'Bài/trang có trong lần đồng bộ trước nhưng nay không còn xuất bản',
                            'Xác minh thay đổi có chủ đích; nếu URL mất, cân nhắc redirect 301 đã duyệt.'),
    'T-DUPLICATE-COPY': ('P1', 'VERIFIED', 'HIGH', 'Cùng một bài được xuất bản ở nhiều URL (bản sao trùng lặp)',
                         'Chủ sở hữu chọn URL giữ lại (thường là bản gốc); bản thừa chuyển nháp/Thùng rác thủ công hoặc redirect 301 về bản giữ. Engine không tự xóa/sửa.'),
    'T-DUPLICATE-SEO-PLUGIN': ('P1', 'NEEDS_REVIEW', 'HIGH', 'Phát hiện nhiều plugin SEO cùng xuất metadata/schema',
                               'Giữ một plugin SEO (Yoast), tắt chức năng trùng của plugin khác sau khi kiểm tra.'),
    # --- HTTP / indexability -----------------------------------------------------------------
    'T-HTTP-ERROR': ('P0', 'VERIFIED', 'HIGH', 'URL đã xuất bản trả về lỗi HTTP',
                     'Kiểm tra bài trong WordPress; khôi phục nội dung hoặc redirect 301 đã duyệt. Không xóa bài.'),
    'T-HTTP-UNREACHABLE': ('P1', 'NEEDS_REVIEW', 'LOW', 'Không tải được URL (timeout/lỗi mạng từ runner)',
                           'Chạy lại audit; nếu lặp lại, kiểm tra hosting/WAF chặn bot.'),
    'T-REDIRECTED-URL': ('P1', 'VERIFIED', 'MEDIUM', 'URL công khai của bài bị chuyển hướng',
                         'Cập nhật liên kết nội bộ tới URL đích; xác nhận redirect là chủ đích.'),
    'T-NOINDEX': ('P0', 'VERIFIED', 'HIGH', 'Trang đã xuất bản bị noindex',
                  'Xác nhận ý định. Nếu cần index, bỏ noindex trong Yoast (cần duyệt).'),
    'T-ROBOTS-BLOCKED': ('P0', 'VERIFIED', 'HIGH', 'robots.txt chặn Googlebot với URL này',
                         'Sửa quy tắc Disallow trong robots.txt sau khi duyệt.'),
    'T-ROBOTS-DISALLOW-ALL': ('P0', 'VERIFIED', 'HIGH', 'robots.txt chặn toàn bộ website',
                              'Sửa robots.txt ngay sau khi chủ sở hữu xác nhận.'),
    'T-ROBOTS-UNAVAILABLE': ('P2', 'VERIFIED', 'LOW', 'Không đọc được robots.txt',
                             'Đảm bảo /robots.txt trả 200 và khai báo Sitemap.'),
    'T-ROBOTS-NO-SITEMAP': ('P3', 'VERIFIED', 'LOW', 'robots.txt không khai báo Sitemap',
                            'Thêm dòng Sitemap: trỏ tới sitemap_index.xml của Yoast.'),
    'T-HTTPS-REDIRECT': ('P0', 'VERIFIED', 'HIGH', 'HTTP không chuyển hướng về HTTPS',
                         'Bật chuyển hướng 301 HTTP→HTTPS ở hosting.'),
    'T-SOFT-404': ('P1', 'VERIFIED', 'MEDIUM', 'URL không tồn tại không trả 404 (soft 404)',
                   'Cấu hình theme/hosting trả HTTP 404 cho trang không tồn tại.'),
    'T-TRAILING-SLASH-DUP': ('P2', 'VERIFIED', 'MEDIUM', 'Biến thể không có dấu / trả 200 thay vì chuyển hướng',
                             'Đảm bảo một dạng URL duy nhất (301 về dạng có /).'),
    'T-SLOW-RESPONSE': ('P3', 'INFO', 'LOW', 'Phản hồi HTML chậm khi đo từ GitHub runner',
                        'Theo dõi bằng PageSpeed/CrUX; đây không phải Core Web Vitals.'),
    # --- canonical ---------------------------------------------------------------------------
    'T-CANONICAL-MISSING': ('P1', 'VERIFIED', 'MEDIUM', 'Thiếu thẻ canonical',
                            'Bật canonical của Yoast cho loại nội dung này.'),
    'T-CANONICAL-MULTIPLE': ('P1', 'VERIFIED', 'MEDIUM', 'Có nhiều thẻ canonical',
                             'Giữ một canonical (Yoast); tắt canonical do theme/plugin khác tạo.'),
    'T-CANONICAL-MISMATCH': ('P1', 'NEEDS_REVIEW', 'HIGH', 'Canonical trỏ tới URL khác URL của trang',
                             'Xác nhận ý định; nếu không chủ đích, sửa canonical trong Yoast (cần duyệt).'),
    'T-CANONICAL-CROSS-DOMAIN': ('P0', 'VERIFIED', 'HIGH', 'Canonical trỏ sang domain khác',
                                 'Sửa canonical về đúng domain blog sau khi duyệt.'),
    'T-CANONICAL-TARGET-BAD': ('P1', 'VERIFIED', 'HIGH', 'URL canonical không trả 200',
                               'Sửa canonical hoặc khôi phục trang đích.'),
    'T-YOAST-CANONICAL-DIFF': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Canonical trong HTML khác canonical Yoast trả qua REST',
                               'Kiểm tra theme/plugin ghi đè canonical của Yoast.'),
    # --- title / meta / headings -------------------------------------------------------------
    'T-TITLE-MISSING': ('P1', 'VERIFIED', 'MEDIUM', 'Thiếu thẻ <title>', 'Đặt SEO title trong Yoast.'),
    'T-TITLE-DUPLICATE': ('P1', 'VERIFIED', 'MEDIUM', 'SEO title trùng với URL khác',
                          'Viết lại SEO title riêng theo search intent của từng URL (cần duyệt).'),
    'T-TITLE-LONG': ('P3', 'VERIFIED', 'MEDIUM', 'SEO title dài, có thể bị cắt trên kết quả tìm kiếm',
                     'Rút gọn SEO title trong Yoast hoặc rút gọn phần tên site trong mẫu tiêu đề; giữ từ khóa chính ở đầu (cần duyệt).'),
    'T-TITLE-SHORT': ('P2', 'VERIFIED', 'MEDIUM', 'SEO title quá ngắn', 'Bổ sung SEO title mô tả đúng nội dung.'),
    'T-META-DESC-MISSING': ('P2', 'VERIFIED', 'LOW', 'Thiếu meta description',
                            'Viết meta description trong Yoast (cần duyệt).'),
    'T-META-DESC-DUPLICATE': ('P2', 'VERIFIED', 'LOW', 'Meta description trùng với URL khác',
                              'Viết meta description riêng cho từng URL.'),
    'T-META-DESC-MULTIPLE': ('P2', 'VERIFIED', 'LOW', 'Trang có nhiều thẻ meta description',
                             'Giữ một nguồn (Yoast); tắt meta description do theme/plugin khác in ra (cần duyệt).'),
    'T-META-DESC-NOT-YOAST': ('P3', 'INFO', 'LOW', 'Meta description trên HTML không do Yoast quản lý (Yoast để trống)',
                              'Cân nhắc viết meta description trong Yoast cho URL quan trọng và đảm bảo chỉ một nguồn in thẻ (cần duyệt).'),
    'T-META-DESC-LONG': ('P3', 'VERIFIED', 'LOW', 'Meta description dài, có thể bị cắt',
                         'Rút gọn còn khoảng 120–155 ký tự.'),
    'T-META-DESC-SHORT': ('P3', 'VERIFIED', 'LOW', 'Meta description quá ngắn', 'Mở rộng mô tả hữu ích.'),
    'T-H1-MISSING': ('P1', 'VERIFIED', 'MEDIUM', 'Trang không có thẻ H1', 'Kiểm tra template theme hiển thị tiêu đề bằng H1.'),
    'T-H1-MULTIPLE': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Trang có nhiều thẻ H1',
                      'Kiểm tra theme (logo/tên site dạng H1); giữ một H1 cho tiêu đề bài.'),
    'T-H1-TITLE-MISMATCH': ('P3', 'INFO', 'LOW', 'H1 khác tiêu đề bài trong WordPress', 'Xác nhận H1 hiển thị đúng tiêu đề.'),
    'T-HEADING-SKIP': ('P3', 'VERIFIED', 'LOW', 'Cấu trúc heading nhảy cấp', 'Sắp xếp H2→H3 theo thứ bậc.'),
    'T-VIEWPORT-MISSING': ('P1', 'VERIFIED', 'MEDIUM', 'Thiếu meta viewport (mobile)', 'Sửa theme thêm meta viewport.'),
    'T-LANG-MISMATCH': ('P3', 'VERIFIED', 'LOW', 'Thuộc tính lang của HTML không phải tiếng Việt',
                        'Đặt ngôn ngữ site là Tiếng Việt (vi).'),
    'T-MIXED-CONTENT': ('P2', 'VERIFIED', 'LOW', 'Tài nguyên tải qua http:// trên trang https', 'Đổi URL tài nguyên sang https.'),
    # --- images ------------------------------------------------------------------------------
    'T-IMG-ALT-MISSING': ('P2', 'VERIFIED', 'LOW', 'Ảnh thiếu thuộc tính alt', 'Thêm alt mô tả ảnh (cần duyệt nội dung alt).'),
    'T-IMG-NO-DIMENSIONS': ('P3', 'VERIFIED', 'LOW', 'Ảnh thiếu width/height (nguy cơ CLS)', 'Thêm kích thước ảnh.'),
    'T-IMG-HEAVY': ('P2', 'VERIFIED', 'LOW', 'Ảnh dung lượng lớn', 'Nén/đổi định dạng WebP/AVIF, giữ URL.'),
    'T-IMG-BROKEN': ('P1', 'VERIFIED', 'LOW', 'Ảnh lỗi (không trả 200)', 'Thay hoặc tải lại ảnh.'),
    'T-FEATURED-IMAGE-MISSING': ('P2', 'VERIFIED', 'LOW', 'Bài không có ảnh đại diện',
                                 'Thêm ảnh đại diện có bản quyền hợp lệ; Yoast sẽ đưa ảnh vào Article schema và og:image.'),
    'T-OG-IMAGE-MISSING': ('P3', 'VERIFIED', 'LOW', 'Thiếu og:image', 'Thêm ảnh đại diện hoặc ảnh mặc định trong Yoast.'),
    # --- structured data ---------------------------------------------------------------------
    'T-SCHEMA-INVALID': ('P1', 'VERIFIED', 'MEDIUM', 'JSON-LD không hợp lệ', 'Sửa nguồn sinh JSON-LD lỗi.'),
    'T-SCHEMA-DUPLICATE-TYPE': ('P1', 'NEEDS_REVIEW', 'MEDIUM', 'Schema trùng loại thực thể từ nhiều nguồn',
                                'Giữ schema graph của Yoast; tắt schema trùng của theme/plugin khác.'),
    'T-SCHEMA-NON-YOAST': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Có JSON-LD ngoài Yoast trên trang',
                           'Xác định nguồn; tránh trùng với graph Yoast.'),
    'T-SCHEMA-MICRODATA': ('P2', 'NEEDS_REVIEW', 'LOW', 'Theme xuất microdata schema.org song song JSON-LD',
                           'Kiểm tra trùng thực thể; ưu tiên một định dạng.'),
    'T-SCHEMA-ARTICLE-MISSING': ('P2', 'VERIFIED', 'LOW', 'Bài viết không có schema Article/BlogPosting',
                                 'Bật schema bài viết của Yoast cho post type này.'),
    'T-SCHEMA-ARTICLE-INCOMPLETE': ('P2', 'VERIFIED', 'LOW', 'Schema Article thiếu thuộc tính khuyến nghị',
                                    'Bổ sung ảnh đại diện/tác giả/ngày để Yoast xuất đủ thuộc tính.'),
    'T-SCHEMA-BREADCRUMB-MISSING': ('P3', 'VERIFIED', 'LOW', 'Không có BreadcrumbList', 'Bật breadcrumb của Yoast.'),
    # --- sitemap -----------------------------------------------------------------------------
    'T-SITEMAP-UNAVAILABLE': ('P0', 'VERIFIED', 'MEDIUM', 'Không đọc được XML sitemap', 'Bật XML sitemap của Yoast.'),
    'T-SITEMAP-FILE-ERROR': ('P1', 'VERIFIED', 'LOW', 'Một file sitemap lỗi', 'Kiểm tra sitemap con lỗi.'),
    'T-SITEMAP-MISSING-URL': ('P1', 'VERIFIED', 'LOW', 'URL đã xuất bản không có trong sitemap',
                              'Kiểm tra cài đặt Yoast (loại nội dung/noindex) để URL vào sitemap.'),
    'T-SITEMAP-BAD-URL': ('P1', 'VERIFIED', 'LOW', 'Sitemap chứa URL không hợp lệ (không 200/noindex/không trong inventory)',
                          'Loại URL lỗi khỏi sitemap hoặc khôi phục trang.'),
    'T-SITEMAP-CORE-DUPLICATE': ('P2', 'VERIFIED', 'LOW', 'Sitemap lõi WordPress vẫn hoạt động song song Yoast',
                                 'Để Yoast quản lý sitemap duy nhất (wp-sitemap.xml nên chuyển hướng/tắt).'),
    # --- archives ----------------------------------------------------------------------------
    'T-ARCHIVE-ERROR': ('P1', 'VERIFIED', 'MEDIUM', 'Trang chuyên mục/lưu trữ trả lỗi', 'Kiểm tra chuyên mục và permalink.'),
    'T-ARCHIVE-NOINDEX': ('P2', 'NEEDS_REVIEW', 'HIGH', 'Trang chuyên mục bị noindex', 'Xác nhận chủ đích trong Yoast.'),
    'T-ARCHIVE-NO-DESCRIPTION': ('P3', 'INFO', 'LOW', 'Chuyên mục chưa có mô tả giới thiệu (hub mỏng)',
                                 'Viết đoạn giới thiệu chuyên mục làm trang hub (cần duyệt).'),
    'T-PERF-POOR': ('P2', 'VERIFIED', 'LOW', 'PageSpeed (lab/field) dưới ngưỡng tốt', 'Tối ưu tài nguyên theo chẩn đoán Lighthouse.'),
    'T-CWV-NOT-MEASURED': ('P3', 'BLOCKED', 'LOW', 'Chưa đo được Core Web Vitals', 'Cấu hình PSI_API_KEY hoặc kết nối CrUX/GSC.'),
    # --- internal / external links -----------------------------------------------------------
    'L-BROKEN-INTERNAL': ('P1', 'VERIFIED', 'LOW', 'Liên kết nội bộ hỏng', 'Sửa liên kết tới URL đúng (cần duyệt).'),
    'L-REDIRECTED-INTERNAL': ('P2', 'VERIFIED', 'LOW', 'Liên kết nội bộ đi qua chuyển hướng', 'Trỏ thẳng tới URL đích cuối.'),
    'L-BROKEN-EXTERNAL': ('P2', 'VERIFIED', 'LOW', 'Liên kết ngoài hỏng (404/410)', 'Thay bằng nguồn chính thức còn hoạt động.'),
    'L-EXTERNAL-UNVERIFIED': ('P3', 'NEEDS_REVIEW', 'LOW', 'Liên kết ngoài không kiểm tra được (403/429/timeout)',
                              'Kiểm tra thủ công trên trình duyệt; nhiều site chặn bot.'),
    'L-ORPHAN': ('P1', 'VERIFIED', 'LOW', 'Bài không có liên kết nội bộ ngữ cảnh trỏ tới',
                 'Thêm liên kết từ bài liên quan/bài trụ cột theo internal-link-matrix (cần duyệt).'),
    'L-LOW-INBOUND': ('P3', 'VERIFIED', 'LOW', 'Bài chỉ có 1 liên kết nội bộ trỏ tới', 'Bổ sung liên kết từ bài cùng cụm.'),
    'L-NO-OUTBOUND': ('P2', 'VERIFIED', 'LOW', 'Bài không liên kết tới bài nội bộ nào',
                      'Thêm liên kết tới bài trụ cột/bài liên quan (cần duyệt).'),
    'L-WEAK-ANCHOR': ('P3', 'VERIFIED', 'LOW', 'Anchor text chung chung', 'Đổi anchor thành cụm mô tả trang đích.'),
    'L-LONG-ANCHOR': ('P3', 'VERIFIED', 'LOW', 'Anchor text quá dài', 'Rút gọn anchor còn cụm từ mô tả chính.'),
    'L-NOFOLLOW-INTERNAL': ('P3', 'VERIFIED', 'LOW', 'Liên kết nội bộ có rel=nofollow', 'Bỏ nofollow cho liên kết nội bộ.'),
    'L-SELF-LINK': ('P3', 'VERIFIED', 'LOW', 'Bài tự liên kết tới chính nó', 'Bỏ liên kết tự trỏ.'),
    'L-DEEP-PAGE': ('P2', 'VERIFIED', 'LOW', 'Trang nằm sâu (nhiều lần nhấp từ trang chủ)',
                    'Thêm liên kết từ hub/bài trụ cột để giảm độ sâu.'),
    'L-UNREACHABLE': ('P1', 'VERIFIED', 'LOW', 'Không tìm thấy đường liên kết từ trang chủ tới trang',
                      'Thêm trang vào chuyên mục/menu/bài liên quan.'),
    # --- content -----------------------------------------------------------------------------
    'C-THIN': ('P2', 'VERIFIED', 'MEDIUM', 'Nội dung mỏng', 'Mở rộng nội dung có giá trị hoặc gộp vào bài liên quan (cần duyệt).'),
    'C-THIN-PAGE': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Trang dịch vụ/khu vực/hub có ít nội dung biên tập',
                    'Chủ sở hữu bổ sung nội dung thật (dịch vụ, khu vực phục vụ, câu hỏi thường gặp); '
                    'không tự tạo giá, đánh giá hay thông tin doanh nghiệp.'),
    'C-DUPLICATE-CONTENT': ('P1', 'VERIFIED', 'HIGH', 'Nội dung gần như trùng lặp hoàn toàn với URL khác',
                            'Chọn URL chính; viết lại khác biệt hoặc hợp nhất kèm 301 (cần duyệt).'),
    'C-NEAR-DUPLICATE': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Nội dung trùng lặp một phần đáng kể với URL khác',
                         'Viết lại đoạn trùng, làm rõ search intent riêng (cần duyệt).'),
    'C-CANNIBALIZATION': ('P2', 'NEEDS_REVIEW', 'HIGH', 'Hai URL có thể cạnh tranh cùng search intent',
                          'Xác minh bằng GSC; phân biệt intent hoặc hợp nhất (cần duyệt, không tự đổi URL).'),
    'C-NO-SOURCES': ('P2', 'NEEDS_REVIEW', 'LOW', 'Bài không có nguồn tham khảo bên ngoài',
                     'Bổ sung nguồn chính thức cho thông tin dữ kiện.'),
    'C-LEGAL-NO-OFFICIAL-SOURCE': ('P2', 'NEEDS_REVIEW', 'LOW', 'Nhắc quy định pháp luật nhưng không dẫn nguồn chính thức',
                                   'Dẫn văn bản/cổng chính phủ hiện hành (vbpl.vn, chinhphu.vn, *.gov.vn).'),
    'C-FINE-AMOUNT': ('P1', 'NEEDS_REVIEW', 'MEDIUM', 'Nêu mức phạt cụ thể cần đối chiếu văn bản hiện hành',
                      'Đối chiếu Nghị định đang có hiệu lực và dẫn nguồn chính thức.'),
    'C-PRICE-MENTION': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Nội dung nêu số tiền/giá', 'Xác nhận giá với chủ sở hữu/nguồn; ghi rõ thời điểm.'),
    'C-NAP-INCONSISTENT': ('P1', 'NEEDS_REVIEW', 'MEDIUM', 'Thông tin liên hệ (NAP) không nhất quán trên website',
                           'Chủ sở hữu xác nhận NAP chuẩn; thống nhất trên mọi trang và schema.'),
    'C-TIME-SENSITIVE': ('P3', 'NEEDS_REVIEW', 'LOW', 'Nội dung có mốc thời gian cần rà soát định kỳ',
                         'Kiểm tra thông tin còn đúng; cập nhật ngày sửa nếu thay đổi.'),
    # --- AEO / GEO ---------------------------------------------------------------------------
    'A-NO-DIRECT-ANSWER': ('P3', 'NEEDS_REVIEW', 'LOW', 'Đoạn mở đầu chưa trả lời trực tiếp câu hỏi của tiêu đề',
                           'Thêm 1–3 câu trả lời trực tiếp ngay sau tiêu đề.'),
    'A-NO-FAQ': ('P3', 'INFO', 'LOW', 'Bài dạng câu hỏi chưa có phần hỏi đáp',
                 'Cân nhắc thêm FAQ thật sự hữu ích; FAQ rich result của Google hiện rất hạn chế.'),
    'A-NO-STRUCTURE': ('P3', 'INFO', 'LOW', 'Bài không có danh sách/bảng dễ trích xuất', 'Cân nhắc tóm tắt bằng danh sách/bảng.'),
    'A-AUTHOR-GENERIC': ('P2', 'NEEDS_REVIEW', 'LOW', 'Tác giả bài viết hiển thị tên chung chung (vd. "admin")',
                         'Chủ sở hữu đặt tên hiển thị và giới thiệu tác giả thật trong Hồ sơ người dùng WordPress; '
                         'không bịa chuyên môn/kinh nghiệm. Tên hiển thị khác tên đăng nhập.'),
    'A-SCHEMA-DATE-MISSING': ('P2', 'VERIFIED', 'LOW', 'Schema bài viết thiếu ngày xuất bản/cập nhật', 'Kiểm tra cấu hình Yoast.'),
    'A-ENTITY-INCONSISTENT': ('P2', 'NEEDS_REVIEW', 'MEDIUM', 'Tên tổ chức/website không nhất quán trong schema',
                              'Thống nhất tên tổ chức trong Yoast > Site representation.'),
    'A-BRAND-MISMATCH': ('P1', 'NEEDS_REVIEW', 'MEDIUM', 'Tên doanh nghiệp trong nội dung khác tên website/schema',
                         'Chủ sở hữu xác nhận thực thể đúng (tên, địa chỉ, điện thoại, website) rồi thống nhất nội dung, '
                         'Yoast Site representation và trang liên hệ. Engine không tự đổi tên/NAP.'),
    'A-ORG-SAMEAS-MISSING': ('P3', 'INFO', 'LOW', 'Schema Organization không có sameAs', 'Khai báo hồ sơ mạng xã hội chính thức trong Yoast.'),
    'A-AI-CRAWLER-POLICY': ('P3', 'INFO', 'LOW', 'Chính sách robots.txt với crawler AI/tìm kiếm', 'Chủ sở hữu quyết định cho phép hoặc chặn.'),
    'A-YOAST-REST-MISSING': ('P1', 'VERIFIED', 'LOW', 'REST không trả yoast_head_json', 'Kiểm tra Yoast còn hoạt động/REST API của Yoast bật.'),
    'A-FOCUS-KEYPHRASE-BLOCKED': ('P3', 'BLOCKED', 'LOW', 'Không đọc được focus keyphrase Yoast ở chế độ chỉ đọc công khai',
                                  'Cần cơ chế đọc meta Yoast đã xác minh (không ghi qua REST khi chưa duyệt).'),
    'G-GSC-NOT-CONFIGURED': ('P3', 'BLOCKED', 'LOW', 'Chưa kết nối Google Search Console',
                             'Thêm secrets GSC_SERVICE_ACCOUNT_JSON và GSC_PROPERTY để có dữ liệu hiệu suất thật.'),
}


@dataclass
class Issue:
    code: str
    priority: str
    verification: str
    risk: str
    issue: str
    fix: str
    evidence: str = ''
    post_id: object = ''
    matrix_id: object = ''
    url: str = ''
    category: str = ''
    impact: int = 1
    key: str = ''
    checked: str = ''
    extra: dict = field(default_factory=dict)

    def as_dict(self):
        return asdict(self)


def make(code, record=None, url='', evidence='', key_extra='', impact=1, **overrides):
    priority, verification, risk, text, fix = CATALOG[code]
    rec = record or {}
    target = url or rec.get('url', '')
    ident = rec.get('id', '') if rec else ''
    base = f"{rec.get('type', 'url')}:{ident}" if ident != '' else target
    key = f'{code}|{base}' + (f'|{key_extra}' if key_extra else '')
    item = Issue(code=code, priority=overrides.pop('priority', priority),
                 verification=overrides.pop('verification', verification), risk=overrides.pop('risk', risk),
                 issue=overrides.pop('issue', text), fix=overrides.pop('fix', fix),
                 evidence=(evidence or '')[:700], post_id=ident, matrix_id=rec.get('matrix_id') or '',
                 url=target, category=overrides.pop('category', (rec.get('category_paths') or [''])[0] if rec else ''),
                 impact=impact, key=key, checked=overrides.pop('checked', (rec.get('page') or {}).get('crawled_at')
                                                         or rec.get('synced_at') or ''),
                 extra=overrides.pop('extra', {}))
    if overrides:
        raise TypeError(f'Unknown issue fields: {sorted(overrides)}')
    return item


def sort_key(item):
    return (PRIORITY_ORDER[item.priority], VERIFICATION_ORDER[item.verification], -item.impact,
            RISK_ORDER[item.risk], str(item.url), item.code)
