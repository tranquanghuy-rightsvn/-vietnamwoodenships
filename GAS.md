# Guideline GAS CMS — Vietnam Wooden Ships (vietnamwoodenships.com)

Nguồn chốt cho mọi quyết định nghiệp vụ của CMS dự án này. Đọc TOÀN BỘ file này trước khi sửa bất
kỳ file nào trong `gas/` hoặc `scripts/build.py`. Theo playbook chung ở skill
`free-cms-static-site-pipeline` (mẫu gốc: xevip); phần song ngữ + nút dịch lấy theo dự án
`iconic` (miraihrvietnam.com) — `clone-web/iconic/GAS.md` mục II/II-b.

```
0. Phạm vi (khách yêu cầu 19/11/2026: "Quản lý: Sản phẩm, tin tức, người dùng"):
   1. Sản phẩm — full CRUD, song ngữ Việt/Anh, nút dịch Việt -> Anh.
   2. Tin tức (bài viết) — full CRUD, song ngữ Việt/Anh, nút dịch Việt -> Anh.
   3. Quản lý người dùng — root (ngầm định) > admin > editor.
   KHÔNG có: danh mục sản phẩm qua CMS (7 danh mục CỐ ĐỊNH, xem mục II.2), form liên hệ/đơn hàng
   (giỏ hàng + thanh toán của site chỉ lưu localStorage phía khách, không gửi về server), trang
   tĩnh (giới thiệu, liên hệ, hướng dẫn... sửa tay).
   Dữ liệu cũ: 32 sản phẩm + 6 bài tin tức ĐÃ CÓ được đưa HẾT vào CMS ngay từ đầu (khách chọn
   19/11/2026) — trang chi tiết/danh sách do `scripts/build.py` sinh lại từ `data/`.

I. Đăng nhập (giống mặc định playbook, gas-backend-patterns.md mục 1/1b/2):
  1. Luồng: nhập email -> gửi OTP -> nhập mã -> vào Admin. Không mật khẩu, không dựa session Google.
  2. Chỉ email có trong sheet `Users` mới được gửi OTP — NGOẠI TRỪ chủ script (ownerEmail_()).
  3. Chủ script (người deploy) LUÔN là `root` ngầm định — không lưu trong `Users`, không hiện
     trong UI quản lý người dùng.
  4. Phân quyền 3 cấp `root > admin > editor` (khách chọn 19/11/2026):
     - `editor`: CRUD sản phẩm + tin tức (cả 2 ngôn ngữ), dùng nút dịch. KHÔNG thấy tab "Người
       dùng" (ẩn UI + server chặn).
     - `admin`: mọi quyền của editor + thêm/sửa/xoá user cấp `editor`.
     - `root`: mọi quyền của admin + thêm/sửa/xoá user cấp `admin`.
     - Không ai tự sửa/xoá chính mình (chặn server). Dòng `root` không bao giờ hiện/sửa qua CMS.
  5. OTP 6 số, sống 10 phút, cooldown 60 giây/email, tối đa 5 lần nhập sai rồi phải xin mã mới.
     Token phiên sống 30 ngày, lưu localStorage; `verifyOtp` dọn token hết hạn
     (`purgeExpiredTokens_`), Đăng xuất thu hồi token ở server (`logout`).
  6. Server luôn tự `requireRole_` ở MỌI hàm.
  7. Email OTP (chốt 19/11/2026 — khách lớn tuổi khó chép mã): email HTML, mã ở ĐẦU tiêu đề (điện
     thoại gợi ý tự điền) + mã to trong ô riêng (chạm 1 lần chọn hết). Email không chạy được
     JavaScript nên KHÔNG có nút "chép" thật sự. KHÔNG có link/nút "Đăng nhập ngay" — đã thử rồi
     bỏ (khách yêu cầu 19/11/2026): mở thêm tab trong lúc đang nhập mã ở tab khác gây lỗi.

II. Sản phẩm — full CRUD, SONG NGỮ:
  1. Luồng nhập: nhập bản Việt trước. Khối English có nút "🌐 Dịch sang English" đặt ngay trước
     khối đó — bấm chỉ dịch + điền sẵn khối English (gọi `translateProduct`), không lưu gì; người
     dùng sửa lại tuỳ ý rồi bấm "Lưu sản phẩm" (lưu cả 2 ngôn ngữ trong 1 lời gọi `saveProduct`).
     Dịch máy (LanguageApp) — người viết tự đọc lại bản English, CMS không bảo đảm đúng 100%.
  2. Field CÓ ô nhập:
     - Tên: `nameVi` (BẮT BUỘC), `nameEn` (tuỳ chọn — để trống thì sản phẩm KHÔNG có trang tiếng
       Anh, không xuất hiện ở các trang tiếng Anh).
     - Slug: `slug` = slugify(`nameVi`) — URL `/sp/<slug>/`; `slugEn` = slugify(`nameEn`) — URL
       `/product/<slugEn>/`. Tự sinh, ô slug chỉ hiện để xem/sửa TRƯỚC lần Lưu đầu. `slug` bất biến
       sau lần Lưu đầu; `slugEn` bất biến kể từ lần Lưu đầu tiên có `nameEn` (xem mục III).
     - Mã SP: `sku` (dùng chung 2 ngôn ngữ, tuỳ chọn).
     - Danh mục: `cat` — dropdown 7 danh mục CỐ ĐỊNH, lưu `slug` tiếng Việt của danh mục
       (`CATEGORIES` trong Code.js và scripts/build.py, PHẢI giống nhau):
         tau-du-lich-du-thuyen  Tàu Du Lịch – Du Thuyền  | cruise-ships-yachts  Cruise Ships – Yachts
         tau-cho-hang           Tàu Chở Hàng             | cargo-ships          Cargo Ships
         thuyen-buom            Thuyền Buồm              | sailing-boats        Sailing Boats
         thuyen-dung-di-dao     Thuyền (Dùng đi dạo)     | leisure-boats        Boats (For Leisure)
         du-thuyen-hien-dai     Du Thuyền Hiện Đại       | modern-yachts        Modern Yachts
         noi-that               Nội Thất                 | furniture            Furniture
         san-pham-khac          Sản Phẩm Khác            | other-products       Other Products
     - Kích thước: `size` (chuỗi tự do, dùng chung, vd "80L x 17W x 74H (cm)").
     - Giá: `price` — số nguyên VNĐ; để trống = "Liên hệ" / "Contact us" (null).
     - Ghi chú giá: `priceNoteVi`, `priceNoteEn` — văn bản nhiều dòng (vd "Giá sỉ: 3.900.000 ₫ –
       đơn tối thiểu 20 cái"), hiện trong khối "Mô tả" cạnh nút mua.
     - Meta description: `metaVi`, `metaEn` (≤ 160 ký tự; trống -> build tự lấy câu đầu phần
       giới thiệu).
     - Ảnh: `images` — mảng đường dẫn tuyệt đối từ gốc site (vd "/assets/img/2022/11/IMG_3700.gif",
       "/assets/uploads/sp/victory/03.jpg"). Ảnh đầu = ảnh chính (thẻ sản phẩm, og:image), ảnh thứ
       2 = ảnh hiện khi rê chuột. Thêm nhiều ảnh, kéo đổi thứ tự, gỡ từng ảnh.
     - Giới thiệu: `introVi`, `introEn` — TinyMCE (h3, p, strong, em, ul/ol, link, CÓ nút
       "Chèn ảnh" nhanh mở thẳng file picker — gas-backend-patterns.md mục 4/4b, ảnh bọc
       `<figure>` + caption, alt = caption hoặc tên sản phẩm). Hiện ở mục "Giới thiệu sản phẩm".
     - Trạng thái: `status` = "published" | "hidden" (ẩn = không build trang, không hiện ở danh
       sách/sitemap; dữ liệu vẫn giữ).
  3. Field KHÔNG có ô nhập (server/build tự suy ra):
     - `updatedAt` (server, ISO).
     - Tên danh mục, giá hiển thị, sản phẩm tương tự (4 SP cùng danh mục), JSON-LD, canonical,
       hreflang — build tự tính.
     - Thứ tự hiển thị = thứ tự trong `data/products.json`; sản phẩm MỚI lên ĐẦU (như mẫu adzo,
       khách yêu cầu 19/11/2026). Sửa sản phẩm cũ giữ nguyên vị trí.
  4. Danh sách trong Admin: đọc `data/products.json` qua GitHub Contents API trong `boot()`; mở
     sửa mới tải `data/products/<slug>.json`.
  5. Ảnh: nén phía client (canvas) cạnh dài tối đa 1600px, JPEG 0.85 (giữ PNG nếu có trong suốt).
     Upload thẳng GitHub ngay khi chọn (không qua Drive). Ảnh CMS RIÊNG 1-1 theo sản phẩm, đặt
     tên như dự án mẫu adzo: `html/assets/uploads/sp/<slug>/gNN.jpg` (ảnh sản phẩm) và `cNN.jpg`
     (ảnh trong giới thiệu); tin tức: `html/assets/uploads/tin-tuc/<slug>/cover.jpg` + `cNN.jpg`.
     Đánh số tăng dần có khoá (tải song song không trùng số), không đánh số lại. Ảnh cũ
     (`/assets/img/...`, có trước CMS) là ảnh DÙNG CHUNG — KHÔNG BAO GIỜ bị xoá qua CMS.

III. Sửa sản phẩm / tin tức:
   - `slug` bất biến sau lần Lưu đầu; `slugEn` bất biến kể từ khi đã có — chặn SERVER (throw) +
     CLIENT (disable ô). Form tái sử dụng DOM: mở form tạo mới phải bật lại ô slug.
   - Ảnh trong editor hiển thị bằng URL tuyệt đối `raw.githubusercontent.com/<owner>/<repo>/
     <branch>/html<path>`; đổi ngược về đường dẫn `/assets/...` trước khi lưu (data và site thật
     KHÔNG BAO GIỜ chứa raw.githubusercontent.com) — iconic GAS.md mục X.
   - Gỡ ảnh khỏi `images` của sản phẩm: chỉ file nằm trong `html/assets/uploads/sp/<slug>/` mới bị
     xoá khỏi repo lúc Lưu (đồng bộ xoá); ảnh `/assets/img/...` chỉ bị gỡ khỏi danh sách.

IV. Xoá:
   - Xoá sản phẩm: `data/products/<slug>.json` + thư mục `html/assets/uploads/sp/<slug>/` + gỡ khỏi
     `data/products.json` (ghi SAU CÙNG). Build tự xoá trang `/sp/<slug>/`, `/product/<slugEn>/`.
   - Xoá bài viết: tương tự với `data/news/<slug>.json`, `html/assets/uploads/tin-tuc/<slug>/`,
     `data/news.json`.
   - Luôn hỏi xác nhận (modal Huỷ/Xoá) trước — không hoàn tác được.

V. Tin tức — full CRUD, SONG NGỮ (cùng nguyên tắc mục II.1 — nút "🌐 Dịch sang English",
   `translatePost`):
   - `titleVi` (BẮT BUỘC), `titleEn` (tuỳ chọn — trống = không có bản tiếng Anh).
   - `slug` = slugify(`titleVi`) -> `/tin-tuc/<slug>/`; `slugEn` = slugify(`titleEn`) ->
     `/news/<slugEn>/`. Bất biến như mục III.
   - Chuyên mục `tag`: "Kiến thức" | "Sản phẩm" | "Hướng dẫn" (cố định; tiếng Anh build tự đổi:
     Knowledge | Products | Guides).
   - Mô tả SEO `descVi`, `descEn` (dùng cho meta description + thẻ tin tức).
   - Ảnh bìa `cover` (dùng chung 2 ngôn ngữ): ảnh CMS ở `html/assets/uploads/tin-tuc/<slug>/`,
     ảnh cũ giữ nguyên đường dẫn.
   - Nội dung `contentVi`, `contentEn` — TinyMCE (h2 có id, h3, p, list, bảng, blockquote, link,
     CÓ nút chèn ảnh nhanh + caption như mục II.2). Mục lục, thời gian đọc, bài liên quan: build
     tự sinh.
   - Ngày đăng `date` (yyyy-MM-dd, mặc định hôm nay), Trạng thái `status` như sản phẩm.
   - Danh sách: `data/news.json` (index, mới nhất lên đầu theo `date`); chi tiết
     `data/news/<slug>.json`.

V-b. Quy tắc dịch (nút "🌐 Dịch sang English" của sản phẩm + tin tức, chốt 19/11/2026):
   - Dịch máy phần chữ, giữ nguyên cấu trúc HTML/ảnh; dịch cả `alt`/`title` của ảnh và caption.
   - Link nội bộ trong bản dịch tự đổi sang trang tiếng Anh tương ứng (`localizeLinksEn_`):
     /sp/<slug>/ -> /product/<slugEn>/ (chưa có bản Anh -> /products/), /danh-muc/<cat>/ ->
     /category/<catEn>/, /tin-tuc/<slug>/ -> /news/<slugEn>/ (chưa có -> /news/), trang tĩnh
     (/lien-he/ -> /contact/, /huong-dan-mua-hang/ -> /buying-guide/...). Link ra ngoài giữ nguyên.
   - Bỏ `id` tiếng Việt của h2/h3 — build tự sinh id tiếng Anh theo chữ tiêu đề.
   - Bài/sản phẩm có bản Anh: build tự khai báo canonical riêng từng bản + `hreflang` vi ↔ en trỏ
     qua lại + `x-default` = bản Việt (Google hiểu là 2 phiên bản của cùng 1 nội dung); nút đổi
     ngôn ngữ trên header trỏ đúng bài tương ứng. Chỉ khai báo ngôn ngữ CÓ trang thật (không có ja).

VI. Form công khai: KHÔNG áp dụng cho dự án này (mục 0).

VII. UX chung (mặc định playbook, gas-backend-patterns.md mục 9/16/17/17b/18):
   - Modal XÁC NHẬN (Huỷ/Xoá) và modal THÔNG BÁO (1 nút Đóng, không tự ẩn); sau mọi lưu/xoá thành
     công nhắc "Cần khoảng 1–2 phút để website cập nhật".
   - Mọi nút async: disable + spinner, tự phục hồi khi lỗi.
   - Mở sản phẩm/bài viết để sửa (cả tạo mới): loading GIỮA MÀN HÌNH (`#page-loading`, phủ mờ chặn
     thao tác) tới khi nội dung VI + EN đã nạp xong vào 2 ô soạn — không chỉ tới lúc server trả về
     (`loadingUntil_` trong js.html; bộ đếm tránh bài mở trước tắt loading của bài mở sau). Lỗi
     tải → tắt loading, hiện modal lỗi, quay về danh sách. (Yêu cầu khách 19/11/2026.)
   - Lưu/Xoá xong: quay về danh sách của đúng mục đó, danh sách tự cập nhật (đồng bộ boot cache).
   - Đổi tab chỉ là hiệu ứng giao diện. Lần đầu: 1 lượt `boot(token)`; lần sau: hiện từ cache rồi
     làm mới ngầm. Key localStorage (trừ token) mang `CLIENT_BUILD` (server tự băm từ app.html +
     js.html) và tự dọn key bản cũ. Khối `if (TOKEN) bootApp()` LUÔN ở cuối js.html.
   - Ô TinyMCE Việt + Anh nằm cùng lúc trong DOM; chỉ init sau khi tab editor đã hiện (gotcha #24).
   - Không lộ tên hạ tầng (Sheet/Drive/Apps Script/GitHub) trong mọi chữ gửi xuống trình duyệt.

VIII. Kiến trúc lưu trữ:
   - Google Sheet `Vietnam Wooden Ships CMS` (tự tạo lần đầu, ID lưu `SPREADSHEET_ID`):
     - `Users` — cột `email`, `role` (`admin` | `editor`).
   - GitHub (Contents API, repo `tranquanghuy-rightsvn/-vietnamwoodenships`, nhánh `master`):
     - `data/products.json` — index: [{slug, slugEn, sku, cat, nameVi, nameEn, size, price, image,
       image2, status, updatedAt}] (thứ tự = thứ tự hiển thị).
     - `data/products/<slug>.json` — đầy đủ: index + priceNoteVi, priceNoteEn, metaVi, metaEn,
       images, introVi, introEn.
     - `data/news.json` — index: [{slug, slugEn, tag, titleVi, titleEn, descVi, descEn, cover,
       date, status, updatedAt}].
     - `data/news/<slug>.json` — đầy đủ: index + contentVi, contentEn.
     - `html/assets/uploads/sp/<slug>/*`, `html/assets/uploads/tin-tuc/<slug>/*` — ảnh CMS, ghi
       THẲNG vào site.
   - Mọi commit của CMS có hậu tố `[CI-Skip]` (Cloudflare bỏ qua deploy, chỉ deploy commit build
     của CI; GitHub Actions vẫn chạy) — như adzo.
   - `data/products.json` / `data/news.json` LUÔN ghi SAU CÙNG — 2 file trigger GitHub Actions
     (`.github/workflows/build.yml`: `python3 scripts/build.py` -> commit `html/`).
   - Độ trễ từ lúc Lưu tới lúc thấy trên site: ~1–2 phút (Actions build + Cloudflare deploy).

IX. Bug đã gặp ở dự án này (cập nhật dần):
   - NGUYÊN NHÂN GỐC của "vài giây là mất / không đặt chuột vào gõ được" (19/11/2026): trên trang
     thật (độ trễ server vài giây, nhúng nhiều lớp iframe) khung soạn của TinyMCE - tạo bằng
     srcdoc trên Chrome - bị trình duyệt NẠP LẠI thành trang trắng vài giây sau khi đã có nội
     dung: mất hết nội dung + ảnh, khung chết (gõ không ăn). Trang test giả lập (trả lời tức thì)
     KHÔNG tái hiện được -> PHẢI test trên trang thật: Cmd+Shift+R, mở bài ngay, chờ ~10 giây.
     Vá 2 lớp (js.html): (1) init_content_sync: true - ghi thẳng khung soạn, không dùng srcdoc;
     (2) watchEditorFrame_(): khung soạn vẫn bị nạp lại vì lý do khác -> tự dựng lại ô soạn và nạp
     lại nội dung mới nhất (LAST_HTML, cập nhật mỗi lần gõ). Test trên trang thật: tải lại cứng +
     mở ngay 3 lần, gõ/xoá/chờ - không mất.
   - MẤT TOÀN BỘ NỘI DUNG + ẢNH khi soạn (19/11/2026, khách báo "vài giây là mất"): mốc hoàn tác
     đầu tiên của TinyMCE là ô RỖNG lúc khởi tạo, ô soạn lại dùng chung giữa các lần mở bài -> 1 lần
     Ctrl+Z / nút Hoàn tác (hoặc lịch sử hoàn tác của bài trước) là xoá sạch. Mẫu adzo cũng dính.
     Vá: mọi lần nạp bài đi qua loadEditor_() (setContent + undoManager.clear() + add()); điền bản
     dịch qua replaceEditorContent_() (1 bước hoàn tác được).
   - Ảnh bị nuốt/xoá khi gõ quanh ảnh: Backspace ở đầu dòng dưới ảnh (kể cả Backspace bộ gõ tiếng
     Việt tự gửi) nhập dòng vào khối ảnh rồi xoá ảnh; gõ khi đang chọn ảnh -> chữ thay ảnh; bấm cạnh
     ảnh rồi gõ -> chữ chui vào khối ảnh. Vá: guardFigureKeys_() - ảnh CHỈ bị xoá khi chọn ảnh rồi
     bấm Delete/Backspace; gõ chữ quanh ảnh tự xuống dòng dưới ảnh. Đã test bằng phím thật.
   - Đặt con trỏ ngay sau ảnh (hoặc trong caption) rồi Enter -> ảnh biến mất + lỗi "Script error."
     (thật ra TinyMCE ném "The new child element contains the parent": nó không có xử lý cho
     <figure> thường - mẫu adzo cũng dính). Vá: bắt phím Enter trong setup (js.html, trước bộ xử
     lý của TinyMCE) - con trỏ trong figure thì tạo <p> mới ngay dưới ảnh (đứng trước ảnh thì ngay
     trên) và đưa con trỏ vào đó. Đã test thật: sau ảnh / trong caption / trước ảnh - không lỗi.
   - Phần giới thiệu chỉ có ảnh (không chữ) từng bị build ẩn mất -> build chỉ ẩn mục "Giới thiệu
     sản phẩm" khi KHÔNG có cả chữ lẫn ảnh; luôn bỏ các dòng trống <p>&nbsp;</p>.
   - Bản CMS đầu tiên (19/11/2026) viết tay lệch khỏi dự án mẫu -> trình soạn thảo lỗi "Script error.",
     chèn ảnh báo "node cannot be null" (tự bọc ảnh vào figure ngay trong NodeChange + bật
     paste_data_images), form chia 2 cột khó dùng. Đã ĐẬP ĐI LÀM LẠI toàn bộ gas/ bám sát khung
     adzo (cùng tên hàm/luồng xử lý), chỉ thêm phần song ngữ theo iconic. Đã chạy thử thật trên
     Chrome bằng trang test giả lập server: mở bài cũ (giữ đủ hỏi đáp/khung lưu ý/bảng/ảnh), chèn
     3 ảnh cùng lúc, dịch, lưu, tạo sản phẩm/bài mới, người dùng - không lỗi. QUY TẮC: sửa gas/ thì
     copy từ mẫu adzo/xevip trước, không tự chế.
   - Deploy version mới xong, URL /exec trả 403 "Truy cập bị từ chối" — code mới dùng thêm dịch
     vụ (bảng tính, mail, gọi API ngoài, dịch) mà chủ script chưa cấp quyền (gotcha #5). Vá: chạy
     hàm `setup()` 1 lần trong trình soạn Apps Script (cấp đủ quyền + tạo bảng Users + báo thiếu
     Script Property).

X. Script Properties (tên CỐ ĐỊNH; giá trị người deploy tự điền):
   - `GITHUB_TOKEN` — fine-grained PAT, Contents: Read and write, chỉ repo `-vietnamwoodenships`.
   - `GITHUB_OWNER` = `tranquanghuy-rightsvn`
   - `GITHUB_REPO` = `-vietnamwoodenships`
   - `GITHUB_BRANCH` = `master`
   - `SPREADSHEET_ID` — KHÔNG tự điền, code tự tạo.
```

## Ghi chú triển khai riêng

- Build script: **Python** (`scripts/build.py`, stdlib) — repo vốn dùng Python cho mọi script.
  Sau build chạy `scripts/seo.py` (meta/canonical/JSON-LD/sitemap).
- URL dạng `/slug/` (thư mục + index.html), link tuyệt đối từ gốc — xem README mục URLs.
- TinyMCE tự host ở `html/vendor/tinymce/` (copy từ dự án iconic, bản đã kiểm chứng trong iframe).
- Trang `/admin/` nhúng web app bằng iframe (mẫu xevip), có link thoát mở thẳng URL `/exec` khi
  nhúng bị treo; `noindex` bằng meta + `html/_headers` (site chạy trên Cloudflare), KHÔNG khai
  trong robots.txt.
- URL web app: `https://script.google.com/macros/s/AKfycbyCYmMtHvwqeau8tFK-Y69DhffNdfs6bf5_ctx8dyVcURW9SX7XD6dGgvB4CoJvT_2R9A/exec`
  (scriptId `1om0JoPPMe3Y2HfspuYCG_GAWNvr4801CkRwVg-RQuyWk_4cYICRZG2MO`). Deploy lại bằng New
  version để giữ URL.

## Deploy GAS (gas/ không nằm trong git)

1. `cd gas && npx @google/clasp@3.0.6-alpha push -f` (đã có `.clasp.json` trỏ scriptId ở trên).
2. `npx @google/clasp@3.0.6-alpha create-deployment -i AKfycbyCYmMtHvwqeau8tFK-Y69DhffNdfs6bf5_ctx8dyVcURW9SX7XD6dGgvB4CoJvT_2R9A -d "<ghi chú>"`
   — tạo version mới cho ĐÚNG deployment cũ, URL không đổi (không dùng "New deployment").
3. Lần đầu / khi code dùng thêm dịch vụ Google mới: mở script.google.com -> project -> chọn hàm
   `setup` -> Run -> cấp quyền. Xem log để biết Script Property nào còn thiếu.
4. Sửa `gas/app.html`/`gas/js.html` không cần bump gì (CLIENT_BUILD tự băm). Trước khi push chạy
   `node scripts/check_gas_client.mjs` (hook trong `.claude/settings.json` tự chạy khi sửa gas/).
