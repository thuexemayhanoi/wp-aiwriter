# SEO Dashboard — https://blog.rentbikehanoi.com

Cập nhật: **2026-10-16T19:16:04+00:00** · Lần chạy: https://github.com/thuexemayhanoi/wp-aiwriter/actions/runs/38952580306 · Chế độ: `matrix` · **Chỉ đọc**: engine không ghi vào WordPress.

## Tổng quan inventory

| Bài viết | Trang | Chuyên mục | Thẻ | Media | URL trong sitemap |
|---|---|---|---|---|---|
| 507 | 18 | 22 | 4 | 58 | 548 |

Crawl: 525 bài/trang tải mới, 0 dùng lại, 175 trang chuyên mục/lưu trữ, 9 link nội bộ khác, 748 request.

## Vấn đề theo mức ưu tiên

| Ưu tiên | Đã xác minh | Cần người duyệt | Thông tin | Bị chặn | Tổng |
|---|---|---|---|---|---|
| P0 | 0 | 0 | 0 | 0 | 0 |
| P1 | 8 | 43 | 0 | 0 | 51 |
| P2 | 1151 | 432 | 0 | 0 | 1583 |
| P3 | 981 | 340 | 110 | 3 | 1434 |

So với lần trước: **1 mới**, **1 đã hết**.

## Mã lỗi phổ biến

| Mã | Ưu tiên | Xác minh | Số lượng |
|---|---|---|---|
| C-FINE-AMOUNT | P1 | NEEDS_REVIEW | 41 |
| T-DUPLICATE-COPY | P1 | VERIFIED | 6 |
| T-TITLE-DUPLICATE | P1 | VERIFIED | 2 |
| A-BRAND-MISMATCH | P1 | NEEDS_REVIEW | 1 |
| C-NAP-INCONSISTENT | P1 | NEEDS_REVIEW | 1 |
| T-FEATURED-IMAGE-MISSING | P2 | VERIFIED | 474 |
| L-ORPHAN | P2 | VERIFIED | 380 |
| L-NO-OUTBOUND | P2 | VERIFIED | 167 |
| C-NO-SOURCES | P2 | NEEDS_REVIEW | 154 |
| C-LEGAL-NO-OFFICIAL-SOURCE | P2 | NEEDS_REVIEW | 154 |
| C-PRICE-MENTION | P2 | NEEDS_REVIEW | 107 |
| L-DEEP-PAGE | P2 | VERIFIED | 74 |
| L-BROKEN-EXTERNAL | P2 | VERIFIED | 34 |
| T-META-DESC-MISSING | P2 | VERIFIED | 19 |
| C-THIN-PAGE | P2 | NEEDS_REVIEW | 7 |
| T-ARCHIVE-NOINDEX | P2 | NEEDS_REVIEW | 7 |
| T-IMG-HEAVY | P2 | VERIFIED | 2 |
| T-SCHEMA-NON-YOAST | P2 | NEEDS_REVIEW | 2 |
| T-UNCATEGORIZED | P2 | VERIFIED | 1 |
| A-AUTHOR-GENERIC | P2 | NEEDS_REVIEW | 1 |
| T-OG-IMAGE-MISSING | P3 | VERIFIED | 492 |
| T-TITLE-LONG | P3 | VERIFIED | 461 |
| L-EXTERNAL-UNVERIFIED | P3 | NEEDS_REVIEW | 125 |
| C-TIME-SENSITIVE | P3 | NEEDS_REVIEW | 121 |
| A-NO-STRUCTURE | P3 | INFO | 102 |

## Cần chủ sở hữu quyết định (engine không tự sửa)

- **6 bản sao trùng lặp đang xuất bản** (giữ bản gốc, bản thừa xử lý thủ công/301):
  - WP 821 https://blog.rentbikehanoi.com/0165-3/ — trùng nội dung với WP 814 https://blog.rentbikehanoi.com/0165-2/ (Excel #165); chuyên mục bản này: Cẩm nang > Hãng xe
  - WP 824 https://blog.rentbikehanoi.com/0165-4/ — trùng nội dung với WP 814 https://blog.rentbikehanoi.com/0165-2/ (Excel #165); chuyên mục bản này: Cẩm nang > Hãng xe
  - WP 827 https://blog.rentbikehanoi.com/0165-5/ — trùng nội dung với WP 814 https://blog.rentbikehanoi.com/0165-2/ (Excel #165); chuyên mục bản này: Cẩm nang > Hãng xe
  - WP 825 https://blog.rentbikehanoi.com/0166-4/ — trùng nội dung với WP 815 https://blog.rentbikehanoi.com/0166-2/ (Excel #166); chuyên mục bản này: Cẩm nang > Hãng xe
  - WP 826 https://blog.rentbikehanoi.com/0167-4/ — trùng nội dung với WP 823 https://blog.rentbikehanoi.com/0167-3/ (Excel #167); chuyên mục bản này: Cẩm nang > Hãng xe
  - WP 829 https://blog.rentbikehanoi.com/0167-5/ — trùng nội dung với WP 823 https://blog.rentbikehanoi.com/0167-3/ (Excel #167); chuyên mục bản này: Cẩm nang > Hãng xe
- **Tên doanh nghiệp**: schema/site: "Thuê xe máy Nguyễn Hà"; nội dung: "Nguyễn Tú" (51 URL, ví dụ https://blog.rentbikehanoi.com/excel-282-honda-wave-phu-hop-voi-quang-duong-di-lam-ngan-hay-dai/; 16 URL liên kết tới domain chứa "nguyentu"); "Nguyễn Hà" (14 URL)
- **NAP/liên hệ**: nhiều số điện thoại khác nhau: 0942467674 (49 trang, ví dụ https://blog.rentbikehanoi.com/excel-282-honda-wave-phu-hop-voi-quang-duong-di-lam-ngan-hay-dai/); 0334699969 (10 trang, ví dụ https://blog.rentbikehanoi.com/bao-mat/)
- **Tác giả**: 501 bài có schema Person (tác giả) tên chung chung: "admin" (501); ví dụ: https://blog.rentbikehanoi.com/thue-xe-may-theo-ngay-ha-noi/, https://blog.rentbikehanoi.com/thue-xe-may-theo-tuan-ha-noi/
- **Nguồn meta description**: 478/525 bài/trang: yoast_head_json không có description nhưng HTML có thẻ meta description (nguồn khác Yoast in ra); ví dụ: https://blog.rentbikehanoi.com/bao-mat/, https://blog.rentbikehanoi.com/cam-nang/, https://blog.rentbikehanoi.com/hoi-dap/
- **41 bài nêu mức phạt cụ thể**: đối chiếu văn bản hiện hành trước khi giữ/sửa (xem `C-FINE-AMOUNT` trong seo-matrix.csv).
- **7 trang lưu trữ noindex**: xác nhận có chủ đích: https://blog.rentbikehanoi.com/category/cam-nang/ung-dung/, https://blog.rentbikehanoi.com/category/dich-vu/, https://blog.rentbikehanoi.com/category/khu-vuc/, https://blog.rentbikehanoi.com/tag/ben-xe-gia-lam/, https://blog.rentbikehanoi.com/tag/nhan-xe-may-thue/, https://blog.rentbikehanoi.com/tag/thue-xe-may-ha-noi/

## 20 mục P0/P1 đầu tiên

| Ưu tiên | Mã | URL | Bằng chứng | Xác minh |
|---|---|---|---|---|
| P1 | T-DUPLICATE-COPY | https://blog.rentbikehanoi.com/0165-3/ | trùng nội dung với WP 814 https://blog.rentbikehanoi.com/0165-2/ (Excel #165); chuyên mục bản này: Cẩm nang >  | VERIFIED |
| P1 | T-DUPLICATE-COPY | https://blog.rentbikehanoi.com/0165-4/ | trùng nội dung với WP 814 https://blog.rentbikehanoi.com/0165-2/ (Excel #165); chuyên mục bản này: Cẩm nang >  | VERIFIED |
| P1 | T-DUPLICATE-COPY | https://blog.rentbikehanoi.com/0165-5/ | trùng nội dung với WP 814 https://blog.rentbikehanoi.com/0165-2/ (Excel #165); chuyên mục bản này: Cẩm nang >  | VERIFIED |
| P1 | T-DUPLICATE-COPY | https://blog.rentbikehanoi.com/0166-4/ | trùng nội dung với WP 815 https://blog.rentbikehanoi.com/0166-2/ (Excel #166); chuyên mục bản này: Cẩm nang >  | VERIFIED |
| P1 | T-DUPLICATE-COPY | https://blog.rentbikehanoi.com/0167-4/ | trùng nội dung với WP 823 https://blog.rentbikehanoi.com/0167-3/ (Excel #167); chuyên mục bản này: Cẩm nang >  | VERIFIED |
| P1 | T-DUPLICATE-COPY | https://blog.rentbikehanoi.com/0167-5/ | trùng nội dung với WP 823 https://blog.rentbikehanoi.com/0167-3/ (Excel #167); chuyên mục bản này: Cẩm nang >  | VERIFIED |
| P1 | T-TITLE-DUPLICATE | https://blog.rentbikehanoi.com/cam-nang/ | "Cẩm nang - Thuê xe máy Nguyễn Hà" cũng dùng ở: https://blog.rentbikehanoi.com/category/cam-nang/ | VERIFIED |
| P1 | T-TITLE-DUPLICATE | https://blog.rentbikehanoi.com/category/cam-nang/ | "Cẩm nang - Thuê xe máy Nguyễn Hà" cũng dùng ở: https://blog.rentbikehanoi.com/cam-nang/ | VERIFIED |
| P1 | A-BRAND-MISMATCH | https://blog.rentbikehanoi.com/ | schema/site: "Thuê xe máy Nguyễn Hà"; nội dung: "Nguyễn Tú" (51 URL, ví dụ https://blog.rentbikehanoi.com/exce | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-xe-may-trong-pho-nho-cach-xu-ly-khi-o-to-dung-do-hai-ben/ | …ượt xe trong những trường hợp không được vượt: phạt tiền từ 800.000 đồng đến 1.000.000 đồng. Xe máy vượt xe,  | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-xe-may-o-khu-vuc-nhieu-pho-mot-chieu-nen-chuan-bi-lo-trinh-the-nao/ | …đi ngược chiều của đường một chiều bị phạt từ 4.000.000 đến 6.000.000 đồng và bị trừ 2 điểm giấy phép lái xe, | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-dung-lan-xe-may-tren-duong-nhieu-lan-cach-nhan-biet-nhanh/ | …áy, lỗi đi không đúng làn đường hiện bị phạt từ 600.000 đến 800.000 đồng; nếu đi sai làn mà gây tai nạn, mức  | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-xe-may-gan-benh-vien-dong-xe-cach-chon-diem-dung-hop-ly-an-toan-va-khong-bi-phat/ | …ưu tiên đang phát tín hiệu ưu tiên bị phạt từ 4.000.000 đến 6.000.000 đồng, đồng thời bị trừ 4 điểm giấy phép | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/bien-cam-re-va-cam-quay-dau-o-ha-noi-nguoi-di-xe-may-can-chu-y-gi/ | …n gây tai nạn giao thông, khung xử phạt tăng vọt lên tới 10–14 triệu đồng kèm trừ điểm giấy phép lái xe nặng. | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/chuyen-lan-bang-xe-may-trong-gio-cao-diem-nhung-loi-nen-tranh/ | …Về luật, đó là không đi đúng làn đường , mức phạt 600.000 – 800.000 đồng, và là một trong những lỗi dễ bị cam | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-xe-may-quanh-ben-xe-nhung-tinh-huong-giao-thong-de-gap/ | …ần đường chỉ đủ cho một làn xe cơ giới: phạt từ 800.000 đến 1.000.000 đồng. Xe kinh doanh vận tải hành khách  | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/cach-dung-ban-do-de-tranh-tuyen-dang-un-tac-khi-di-xe-may/ | …i. Đi xe máy ngược chiều đường một chiều hiện bị phạt 4 đến 6 triệu đồng và trừ 2 điểm giấy phép lái xe — mức | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-xe-may-trong-ngo-hep-ha-noi-cach-tranh-va-quet-khi-gap-xe-nguoc-chieu/ | …và thói quen “leo lề” để tránh chui ngõ bị phạt 4.000.000 – 6.000.000 đồng, trừ 2 điểm giấy phép lái xe. Luật | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/di-xe-may-qua-cau-vinh-tuy-cach-chuan-bi-lo-trinh-truoc-khi-di/ | …g phần đường: theo Nghị định 168/2024/NĐ-CP, phạt 600.000 – 800.000 đồng. Đây là lỗi dễ dính nhất ở Vĩnh Tuy: | NEEDS_REVIEW |
| P1 | C-FINE-AMOUNT | https://blog.rentbikehanoi.com/cach-gui-xe-may-thue-an-toan-tai-trung-tam-ha-noi/ | …xe trên vỉa hè trái phép có thể bị phạt tiền từ 400.000 đến 600.000 đồng. Vỉa hè, theo Luật Trật tự, an toàn  | NEEDS_REVIEW |

## Liên kết nội bộ

| Liên kết ngữ cảnh | Bài mồ côi | Inbound TB | Độ sâu tối đa | Đề xuất P1/P2/P3 | Có anchor sẵn |
|---|---|---|---|---|---|
| 1053 | 380 | 2.01 | 8 | 580/86/17 | 84 |

Phân bố độ sâu nhấp chuột: 1: 12, 2: 148, 3: 183, 4: 101, 5: 34, 6: 17, 7: 18, 8: 5, unknown: 1

## Nội dung

- Cặp gần trùng lặp: 0; cặp nghi cannibalization: 0 (cần GSC để xác minh); content gap: 22 dòng.
- Số điện thoại tìm thấy trong nội dung: 0942467674 (49 trang), 0334699969 (10 trang)
- Domain ngoài được liên kết nhiều nhất: www.honda.com.vn (133), yamaha-motor.com.vn (114), xaydungchinhsach.chinhphu.vn (83), vinfastauto.com (75), cdn.honda.com.vn (48), support.google.com (45), www.yadea.com.vn (33), support.apple.com (31)

## Kỹ thuật

- robots.txt: HTTP 200; sitemap khai báo: ['https://blog.rentbikehanoi.com/sitemap_index.xml']
- Sitemap: 4 file, 548 URL; wp-sitemap.xml lõi: HTTP 200 (1 chuyển hướng → https://blog.rentbikehanoi.com/sitemap_index.xml)
- HTTP→HTTPS: https://blog.rentbikehanoi.com/; probe 404: HTTP 404
- Yoast: 28.7; theme: ['nguyen-ha-glass-2026']; plugin nhận diện từ HTML: 2

## Core Web Vitals / PageSpeed

Chưa đo trong lần chạy này (BLOCKED/không chạy; HTTP 429). API trả HTTP 429 (hết hạn mức không khóa): thêm secret `PSI_API_KEY`. Không suy đoán số liệu.

## Google Search Console

Trạng thái: **BLOCKED** — GSC_SERVICE_ACCOUNT_JSON / GSC_PROPERTY not configured

## Cách dùng báo cáo

- `reports/seo-matrix.csv`: toàn bộ vấn đề, sắp P0→P3; cột QA Result phân biệt lỗi đã xác minh và cảnh báo cần người duyệt.
- `reports/internal-link-matrix.csv`: đề xuất liên kết nguồn→đích với anchor có sẵn trong bài; chỉ áp dụng sau khi duyệt.
- `reports/cannibalization.csv`, `reports/content-gaps.csv`: tín hiệu cần người quyết định.
- Ghi trạng thái xử lý vào `data/seo/issue-overrides.json`; chỉ mục trong `data/seo/approved-fixes.json` mới được áp dụng lên WordPress.
