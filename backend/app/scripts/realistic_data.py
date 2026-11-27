"""Dữ liệu nguồn cho seed_realistic.py: sách có thật trên thị trường Việt Nam,
tên người, địa chỉ, câu đánh giá... Tách riêng để script sinh dữ liệu chỉ còn
phần logic mô phỏng.

Giá bìa lấy gần đúng theo mặt bằng giá thị trường; ISBN được sinh ngẫu nhiên
(đúng định dạng 978-604, đúng checksum) chứ không phải ISBN thật của sách.
Địa chỉ dùng cấp hành chính 2 tầng (tỉnh/thành → phường/xã) theo sắp xếp từ
1/7/2025, nên cột district để trống.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Danh mục: (slug, tên, slug cha hoặc None)
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("van-hoc", "Văn học", None),
    ("van-hoc-viet-nam", "Văn học Việt Nam", "van-hoc"),
    ("van-hoc-nuoc-ngoai", "Văn học nước ngoài", "van-hoc"),
    ("trinh-tham", "Trinh thám - Kinh dị", None),
    ("kinh-te", "Kinh tế", None),
    ("ky-nang-song", "Kỹ năng sống", None),
    ("tam-ly-hoc", "Tâm lý học", None),
    ("lich-su", "Lịch sử", None),
    ("khoa-hoc", "Khoa học", None),
    ("thieu-nhi", "Thiếu nhi", None),
    ("truyen-tranh", "Truyện tranh", None),
    ("ngoai-ngu", "Ngoại ngữ", None),
]

# Mã ngắn dùng trong SKU, ví dụ TBS-KN-0007-BM
CATEGORY_CODE = {
    "van-hoc-viet-nam": "VN", "van-hoc-nuoc-ngoai": "NN", "trinh-tham": "TT",
    "kinh-te": "KT", "ky-nang-song": "KN", "tam-ly-hoc": "TL", "lich-su": "LS",
    "khoa-hoc": "KH", "thieu-nhi": "TN", "truyen-tranh": "TR", "ngoai-ngu": "NG",
}

# ---------------------------------------------------------------------------
# Nhà cung cấp: (tên, điện thoại, email, địa chỉ)
# ---------------------------------------------------------------------------
SUPPLIERS = [
    ("NXB Kim Đồng", "02439434730", "lienhe@kimdong.vn", "55 Quang Trung, Phường Cửa Nam, Hà Nội"),
    ("NXB Trẻ", "02839316289", "lienhe@nxbtre.com.vn", "161B Lý Chính Thắng, Phường Xuân Hòa, TP. Hồ Chí Minh"),
    ("Nhã Nam", "02435146876", "lienhe@nhanam.vn", "59 Đỗ Quang, Phường Yên Hòa, Hà Nội"),
    ("Alpha Books", "02437225988", "lienhe@alphabooks.vn", "176 Thái Hà, Phường Đống Đa, Hà Nội"),
    ("First News - Trí Việt", "02838227979", "lienhe@firstnews.com.vn", "11H Nguyễn Thị Minh Khai, Phường Sài Gòn, TP. Hồ Chí Minh"),
    ("Đông A", "02437715325", "lienhe@donga.vn", "113 Đông Các, Phường Đống Đa, Hà Nội"),
    ("Thái Hà Books", "02437930480", "lienhe@thaihabooks.com", "119 Cầu Giấy, Phường Cầu Giấy, Hà Nội"),
    ("Omega Plus", "02432636338", "lienhe@omegaplus.vn", "Số 8 ngõ 5 Láng Hạ, Phường Giảng Võ, Hà Nội"),
    ("MCBooks", "02437921466", "lienhe@mcbooks.vn", "26/245 Mai Dịch, Phường Nghĩa Đô, Hà Nội"),
]

# ---------------------------------------------------------------------------
# Sách: (danh mục, tên, tác giả, NXB, nhà cung cấp, giá bìa, độ phổ biến 1-10,
#        các phiên bản thêm ngoài "Bìa mềm" [(tên, phụ thu)], mô tả, sách mới?)
# Độ phổ biến quyết định số lượng bán ra trong mô phỏng.
# ---------------------------------------------------------------------------
HC = [("Bìa cứng", 70000)]  # phiên bản bìa cứng phổ biến

BOOKS = [
    # --- Văn học Việt Nam ---
    ("van-hoc-viet-nam", "Tôi Thấy Hoa Vàng Trên Cỏ Xanh", "Nguyễn Nhật Ánh", "NXB Trẻ", "NXB Trẻ", 125000, 9, HC,
     "Câu chuyện về tuổi thơ nghèo khó mà trong trẻo của hai anh em Thiều và Tường ở một làng quê miền Trung.", False),
    ("van-hoc-viet-nam", "Cho Tôi Xin Một Vé Đi Tuổi Thơ", "Nguyễn Nhật Ánh", "NXB Trẻ", "NXB Trẻ", 80000, 8, [],
     "Cuốn sách đưa người lớn trở về thế giới tuổi thơ với những trò nghịch ngợm và triết lý hồn nhiên.", False),
    ("van-hoc-viet-nam", "Mắt Biếc", "Nguyễn Nhật Ánh", "NXB Trẻ", "NXB Trẻ", 110000, 8, [("Bìa cứng", 60000)],
     "Mối tình đơn phương dai dẳng của Ngạn dành cho Hà Lan, cô bạn có đôi mắt biếc ở làng Đo Đo.", False),
    ("van-hoc-viet-nam", "Cô Gái Đến Từ Hôm Qua", "Nguyễn Nhật Ánh", "NXB Trẻ", "NXB Trẻ", 95000, 5, [],
     "Thư và cô bạn thuở nhỏ Tiểu Li gặp lại nhau ở tuổi học trò, giữa những trò đùa và rung động đầu đời.", False),
    ("van-hoc-viet-nam", "Ngồi Khóc Trên Cây", "Nguyễn Nhật Ánh", "NXB Trẻ", "NXB Trẻ", 120000, 4, [],
     "Kỳ nghỉ hè ở quê nội của Đông và câu chuyện tình cảm trong sáng với cô bé Rùa.", False),
    ("van-hoc-viet-nam", "Nỗi Buồn Chiến Tranh", "Bảo Ninh", "NXB Trẻ", "NXB Trẻ", 120000, 3, [],
     "Tiểu thuyết về ký ức chiến tranh và tình yêu của người lính Kiên, một trong những tác phẩm Việt được dịch nhiều nhất.", False),
    ("van-hoc-viet-nam", "Cánh Đồng Bất Tận", "Nguyễn Ngọc Tư", "NXB Trẻ", "NXB Trẻ", 90000, 3, [],
     "Tập truyện ngắn về những phận người lênh đênh trên sông nước miền Tây Nam Bộ.", False),
    ("van-hoc-viet-nam", "Nhật Ký Đặng Thùy Trâm", "Đặng Thùy Trâm", "NXB Hội Nhà Văn", "Nhã Nam", 98000, 3, [],
     "Những trang nhật ký của nữ bác sĩ liệt sĩ Đặng Thùy Trâm viết tại chiến trường Đức Phổ.", False),
    ("van-hoc-viet-nam", "Thương Nhớ Mười Hai", "Vũ Bằng", "NXB Văn Học", "Nhã Nam", 105000, 2, [],
     "Tùy bút về mười hai tháng ở Hà Nội và miền Bắc qua nỗi nhớ của người xa quê.", False),
    ("van-hoc-viet-nam", "Tắt Đèn", "Ngô Tất Tố", "NXB Văn Học", "Đông A", 58000, 2, [],
     "Tiểu thuyết hiện thực về chị Dậu và nông thôn Việt Nam trước Cách mạng tháng Tám.", False),
    ("van-hoc-viet-nam", "Tuyển Tập Nam Cao", "Nam Cao", "NXB Văn Học", "Đông A", 135000, 2, [],
     "Tuyển chọn truyện ngắn tiêu biểu của Nam Cao: Chí Phèo, Lão Hạc, Đời thừa, Đôi mắt.", False),
    ("van-hoc-viet-nam", "Vang Bóng Một Thời", "Nguyễn Tuân", "NXB Văn Học", "Đông A", 75000, 1, [],
     "Những thú chơi tao nhã và nét đẹp của một thời đã qua dưới ngòi bút tài hoa của Nguyễn Tuân.", False),
    ("van-hoc-viet-nam", "Hà Nội Băm Sáu Phố Phường", "Thạch Lam", "NXB Văn Học", "Nhã Nam", 68000, 2, [],
     "Tùy bút về món ăn, thú vui và phong vị Hà Nội xưa.", False),
    ("van-hoc-viet-nam", "Truyện Kiều", "Nguyễn Du", "NXB Văn Học", "Đông A", 85000, 3, [("Bìa cứng", 95000)],
     "Kiệt tác thơ lục bát kể về cuộc đời mười lăm năm lưu lạc của Thúy Kiều.", False),

    # --- Văn học nước ngoài ---
    ("van-hoc-nuoc-ngoai", "Rừng Na Uy", "Haruki Murakami", "NXB Hội Nhà Văn", "Nhã Nam", 160000, 6, [],
     "Toru Watanabe nhớ lại những năm đại học ở Tokyo, giữa tình yêu, mất mát và nỗi cô đơn.", False),
    ("van-hoc-nuoc-ngoai", "Kafka Bên Bờ Biển", "Haruki Murakami", "NXB Hội Nhà Văn", "Nhã Nam", 185000, 4, [],
     "Hai câu chuyện song song của cậu bé bỏ nhà ra đi và ông lão biết nói chuyện với mèo.", False),
    ("van-hoc-nuoc-ngoai", "Hoàng Tử Bé", "Antoine de Saint-Exupéry", "NXB Hội Nhà Văn", "Nhã Nam", 75000, 6, [],
     "Cuộc gặp giữa người phi công lạc giữa sa mạc và cậu hoàng tử đến từ tiểu tinh cầu B612.", False),
    ("van-hoc-nuoc-ngoai", "Điều Kỳ Diệu Của Tiệm Tạp Hóa Namiya", "Higashino Keigo", "NXB Hội Nhà Văn", "Nhã Nam", 115000, 7, [],
     "Ba tên trộm trú trong tiệm tạp hóa bỏ hoang và nhận được những lá thư xin lời khuyên từ quá khứ.", False),
    ("van-hoc-nuoc-ngoai", "Bố Già", "Mario Puzo", "NXB Văn Học", "Đông A", 150000, 5, HC,
     "Thế giới mafia Mỹ qua gia đình Corleone và người cha Vito quyền lực.", False),
    ("van-hoc-nuoc-ngoai", "Trăm Năm Cô Đơn", "Gabriel García Márquez", "NXB Văn Học", "Nhã Nam", 175000, 4, [],
     "Bảy thế hệ nhà Buendía ở ngôi làng Macondo, tác phẩm tiêu biểu của chủ nghĩa hiện thực huyền ảo.", False),
    ("van-hoc-nuoc-ngoai", "Giết Con Chim Nhại", "Harper Lee", "NXB Văn Học", "Nhã Nam", 120000, 4, [],
     "Qua mắt cô bé Scout, câu chuyện về công lý và định kiến chủng tộc ở miền Nam nước Mỹ.", False),
    ("van-hoc-nuoc-ngoai", "Kiêu Hãnh Và Định Kiến", "Jane Austen", "NXB Văn Học", "Nhã Nam", 135000, 3, [],
     "Elizabeth Bennet và Mr. Darcy vượt qua kiêu hãnh và định kiến của chính mình.", False),
    ("van-hoc-nuoc-ngoai", "Không Gia Đình", "Hector Malot", "NXB Văn Học", "Đông A", 145000, 2, [],
     "Hành trình lưu lạc của cậu bé Rémi cùng đoàn xiếc thú của cụ Vitalis.", False),
    ("van-hoc-nuoc-ngoai", "Ông Già Và Biển Cả", "Ernest Hemingway", "NXB Văn Học", "Nhã Nam", 60000, 2, [],
     "Cuộc vật lộn ba ngày đêm giữa ông lão Santiago và con cá kiếm khổng lồ.", False),
    ("van-hoc-nuoc-ngoai", "Người Đua Diều", "Khaled Hosseini", "NXB Văn Học", "Nhã Nam", 135000, 4, [],
     "Tình bạn, sự phản bội và chuộc lỗi giữa Amir và Hassan trên nền lịch sử Afghanistan.", False),
    ("van-hoc-nuoc-ngoai", "Suối Nguồn", "Ayn Rand", "NXB Trẻ", "NXB Trẻ", 395000, 2, [],
     "Kiến trúc sư Howard Roark kiên định với lý tưởng sáng tạo trước một xã hội đề cao sự dễ dãi.", False),
    ("van-hoc-nuoc-ngoai", "Harry Potter Và Hòn Đá Phù Thủy", "J.K. Rowling", "NXB Trẻ", "NXB Trẻ", 150000, 7, [("Bìa cứng", 100000)],
     "Năm học đầu tiên của Harry tại trường Phù thủy và Pháp sư Hogwarts.", False),
    ("van-hoc-nuoc-ngoai", "Harry Potter Và Phòng Chứa Bí Mật", "J.K. Rowling", "NXB Trẻ", "NXB Trẻ", 160000, 4, [("Bìa cứng", 100000)],
     "Năm thứ hai ở Hogwarts, những học sinh bị hóa đá và bí mật về Phòng chứa Bí mật.", False),
    ("van-hoc-nuoc-ngoai", "Khi Hơi Thở Hóa Thinh Không", "Paul Kalanithi", "NXB Lao Động", "Alpha Books", 109000, 3, [],
     "Hồi ký của bác sĩ phẫu thuật thần kinh khi đối diện với căn bệnh ung thư phổi giai đoạn cuối.", False),
    ("van-hoc-nuoc-ngoai", "Tiếng Chim Hót Trong Bụi Mận Gai", "Colleen McCullough", "NXB Văn Học", "Đông A", 225000, 2, [],
     "Ba thế hệ gia đình Cleary trên đồng cỏ nước Úc và mối tình cấm đoán của Meggie.", False),
    ("van-hoc-nuoc-ngoai", "Lâu Đài Bay Của Pháp Sư Howl", "Diana Wynne Jones", "NXB Hội Nhà Văn", "Nhã Nam", 128000, 3, [],
     "Cô gái Sophie bị biến thành bà lão và bước vào tòa lâu đài biết di chuyển của pháp sư Howl.", True),

    # --- Trinh thám ---
    ("trinh-tham", "Phía Sau Nghi Can X", "Higashino Keigo", "NXB Hội Nhà Văn", "Nhã Nam", 120000, 6, [],
     "Thầy giáo toán thiên tài dựng nên màn che giấu tội ác hoàn hảo để bảo vệ người phụ nữ hàng xóm.", False),
    ("trinh-tham", "Bạch Dạ Hành", "Higashino Keigo", "NXB Hội Nhà Văn", "Nhã Nam", 185000, 4, [],
     "Vụ án mạng chưa có lời giải năm 1973 và số phận gắn bó của hai đứa trẻ suốt hai mươi năm.", False),
    ("trinh-tham", "Mười Người Da Đen Nhỏ", "Agatha Christie", "NXB Trẻ", "NXB Trẻ", 110000, 5, [],
     "Mười người lạ bị mời đến hòn đảo biệt lập và lần lượt chết theo lời một bài đồng dao.", False),
    ("trinh-tham", "Án Mạng Trên Chuyến Tàu Tốc Hành Phương Đông", "Agatha Christie", "NXB Trẻ", "NXB Trẻ", 105000, 4, [],
     "Thám tử Hercule Poirot điều tra vụ giết người trên chuyến tàu bị kẹt giữa bão tuyết.", False),
    ("trinh-tham", "Sherlock Holmes Toàn Tập", "Arthur Conan Doyle", "NXB Văn Học", "Đông A", 450000, 3, [],
     "Trọn bộ ba tập các vụ án của thám tử Sherlock Holmes và bác sĩ Watson.", False),
    ("trinh-tham", "Mật Mã Da Vinci", "Dan Brown", "NXB Văn Học", "Đông A", 168000, 4, [],
     "Giáo sư Robert Langdon giải mã những bí ẩn ẩn trong tác phẩm của Leonardo da Vinci.", False),
    ("trinh-tham", "Sự Im Lặng Của Bầy Cừu", "Thomas Harris", "NXB Hội Nhà Văn", "Nhã Nam", 128000, 3, [],
     "Thực tập sinh FBI Clarice Starling tìm đến bác sĩ Hannibal Lecter để truy bắt một kẻ giết người hàng loạt.", False),
    ("trinh-tham", "Lời Thú Tội", "Minato Kanae", "NXB Hội Nhà Văn", "Nhã Nam", 98000, 3, [],
     "Bài giảng cuối cùng của cô giáo Moriguchi mở đầu cho một kế hoạch trả thù lạnh lùng.", False),
    ("trinh-tham", "Cô Gái Có Hình Xăm Rồng", "Stieg Larsson", "NXB Hội Nhà Văn", "Nhã Nam", 175000, 2, [],
     "Nhà báo Mikael Blomkvist và hacker Lisbeth Salander điều tra vụ mất tích bốn mươi năm trước.", False),
    ("trinh-tham", "Ác Ý", "Higashino Keigo", "NXB Hội Nhà Văn", "Nhã Nam", 112000, 3, [],
     "Thám tử Kaga lần theo động cơ thật sự phía sau vụ sát hại một nhà văn nổi tiếng.", True),

    # --- Kinh tế ---
    ("kinh-te", "Cha Giàu Cha Nghèo", "Robert Kiyosaki", "NXB Trẻ", "NXB Trẻ", 135000, 6, [],
     "Bài học về tiền bạc và tư duy tài chính qua câu chuyện của hai người cha.", False),
    ("kinh-te", "Nghĩ Giàu Và Làm Giàu", "Napoleon Hill", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 110000, 5, [],
     "Mười ba nguyên tắc thành công đúc kết từ việc phỏng vấn hàng trăm người giàu có.", False),
    ("kinh-te", "Nhà Đầu Tư Thông Minh", "Benjamin Graham", "NXB Thế Giới", "Alpha Books", 245000, 4, HC,
     "Cuốn sách kinh điển về đầu tư giá trị, nền tảng tư duy của Warren Buffett.", False),
    ("kinh-te", "Từ Tốt Đến Vĩ Đại", "Jim Collins", "NXB Trẻ", "NXB Trẻ", 155000, 3, [],
     "Nghiên cứu những công ty vượt từ mức tốt lên vĩ đại và yếu tố làm nên sự khác biệt.", False),
    ("kinh-te", "Tâm Lý Học Về Tiền", "Morgan Housel", "NXB Dân Trí", "Thái Hà Books", 189000, 5, [],
     "Mười chín câu chuyện ngắn về cách con người suy nghĩ và hành xử với tiền bạc.", False),
    ("kinh-te", "Người Giàu Có Nhất Thành Babylon", "George S. Clason", "NXB Lao Động", "Alpha Books", 98000, 4, [],
     "Những nguyên tắc quản lý tài chính cá nhân qua các câu chuyện ngụ ngôn thành Babylon cổ.", False),
    ("kinh-te", "Bí Mật Tư Duy Triệu Phú", "T. Harv Eker", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 108000, 4, [],
     "Khám phá kế hoạch tài chính tiềm thức quyết định thành công về tiền bạc của mỗi người.", False),
    ("kinh-te", "Không Đến Một", "Peter Thiel", "NXB Trẻ", "NXB Trẻ", 128000, 3, [],
     "Bàn về khởi nghiệp và cách xây dựng doanh nghiệp tạo ra điều hoàn toàn mới.", False),
    ("kinh-te", "Chiến Lược Đại Dương Xanh", "W. Chan Kim, Renée Mauborgne", "NXB Lao Động", "Alpha Books", 199000, 2, [],
     "Cách tạo ra khoảng thị trường không có cạnh tranh thay vì lao vào đại dương đỏ.", False),
    ("kinh-te", "Chiến Tranh Tiền Tệ", "Song Hongbing", "NXB Lao Động", "Thái Hà Books", 185000, 3, [],
     "Góc nhìn về lịch sử tài chính thế giới và quyền lực của các định chế ngân hàng.", False),
    ("kinh-te", "Thế Giới Phẳng", "Thomas L. Friedman", "NXB Trẻ", "NXB Trẻ", 230000, 2, [],
     "Toàn cầu hóa và công nghệ đã san phẳng sân chơi kinh tế thế giới như thế nào.", False),
    ("kinh-te", "Kinh Tế Học Hài Hước", "Steven D. Levitt, Stephen J. Dubner", "NXB Lao Động", "Alpha Books", 145000, 2, [],
     "Dùng dữ liệu và tư duy kinh tế học để lý giải những hiện tượng đời thường bất ngờ.", False),

    # --- Kỹ năng sống ---
    ("ky-nang-song", "Đắc Nhân Tâm", "Dale Carnegie", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 86000, 10, [("Bìa cứng", 64000)],
     "Nghệ thuật thu phục lòng người, cuốn sách kỹ năng giao tiếp bán chạy nhất mọi thời đại.", False),
    ("ky-nang-song", "Quẳng Gánh Lo Đi Và Vui Sống", "Dale Carnegie", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 98000, 5, [],
     "Những phương pháp thực tế để thoát khỏi lo âu và tận hưởng cuộc sống.", False),
    ("ky-nang-song", "Thay Đổi Tí Hon Hiệu Quả Bất Ngờ", "James Clear", "NXB Thế Giới", "Alpha Books", 189000, 8, [],
     "Cách xây dựng thói quen tốt và loại bỏ thói quen xấu bằng những thay đổi một phần trăm mỗi ngày.", False),
    ("ky-nang-song", "7 Thói Quen Hiệu Quả", "Stephen R. Covey", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 175000, 5, [],
     "Bảy thói quen của người thành đạt, từ chủ động đến không ngừng hoàn thiện bản thân.", False),
    ("ky-nang-song", "Tuổi Trẻ Đáng Giá Bao Nhiêu", "Rosie Nguyễn", "NXB Hội Nhà Văn", "Nhã Nam", 80000, 7, [],
     "Lời khuyên về đọc sách, học tập, đi và trải nghiệm dành cho người trẻ.", False),
    ("ky-nang-song", "Muôn Kiếp Nhân Sinh", "Nguyên Phong", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 168000, 6, HC,
     "Câu chuyện về luật nhân quả và luân hồi qua những kiếp sống của một doanh nhân.", False),
    ("ky-nang-song", "Hành Trình Về Phương Đông", "Baird T. Spalding", "NXB Thế Giới", "First News - Trí Việt", 98000, 4, [],
     "Ghi chép của đoàn khoa học gia phương Tây trong chuyến khảo cứu huyền học tại Ấn Độ.", False),
    ("ky-nang-song", "Dám Bị Ghét", "Kishimi Ichiro, Koga Fumitake", "NXB Lao Động", "Nhã Nam", 109000, 5, [],
     "Cuộc đối thoại giữa triết gia và chàng thanh niên về tâm lý học Adler và tự do sống là mình.", False),
    ("ky-nang-song", "Hiểu Về Trái Tim", "Minh Niệm", "NXB Tổng hợp TP.HCM", "NXB Trẻ", 158000, 5, [],
     "Những bài viết giúp hiểu và chăm sóc các cảm xúc như cô đơn, ghen tuông, tha thứ.", False),
    ("ky-nang-song", "Đời Ngắn Đừng Ngủ Dài", "Robin Sharma", "NXB Trẻ", "NXB Trẻ", 72000, 4, [],
     "Một trăm lẻ một lời khuyên ngắn gọn để sống trọn vẹn và có ý nghĩa hơn.", False),
    ("ky-nang-song", "Trên Đường Băng", "Tony Buổi Sáng", "NXB Trẻ", "NXB Trẻ", 98000, 4, [],
     "Những bài viết thẳng thắn, hài hước về thái độ sống và làm việc dành cho người trẻ.", False),
    ("ky-nang-song", "Sức Mạnh Của Thói Quen", "Charles Duhigg", "NXB Lao Động", "Alpha Books", 149000, 3, [],
     "Khoa học phía sau vòng lặp thói quen và cách thay đổi chúng ở cá nhân lẫn tổ chức.", False),
    ("ky-nang-song", "Atomic Habits Workbook", "James Clear", "NXB Thế Giới", "Alpha Books", 129000, 3, [],
     "Sổ tay thực hành đi kèm, giúp áp dụng từng bước phương pháp xây dựng thói quen.", True),

    # --- Tâm lý học ---
    ("tam-ly-hoc", "Tư Duy Nhanh Và Chậm", "Daniel Kahneman", "NXB Thế Giới", "Alpha Books", 239000, 4, [],
     "Hai hệ thống tư duy của con người và những thiên kiến chi phối quyết định hằng ngày.", False),
    ("tam-ly-hoc", "Đọc Vị Bất Kỳ Ai", "David J. Lieberman", "NXB Lao Động", "Thái Hà Books", 79000, 4, [],
     "Các kỹ thuật tâm lý để nhận biết suy nghĩ và ý định thật của người đối diện.", False),
    ("tam-ly-hoc", "Trí Tuệ Cảm Xúc", "Daniel Goleman", "NXB Lao Động", "Alpha Books", 189000, 3, [],
     "Vì sao EQ có thể quan trọng hơn IQ trong học tập, công việc và các mối quan hệ.", False),
    ("tam-ly-hoc", "Thiên Tài Bên Trái, Kẻ Điên Bên Phải", "Cao Minh", "NXB Thế Giới", "Thái Hà Books", 139000, 4, [],
     "Những cuộc trò chuyện với bệnh nhân tâm thần hé lộ các góc nhìn khác thường về thế giới.", False),
    ("tam-ly-hoc", "Phi Lý Trí", "Dan Ariely", "NXB Lao Động", "Alpha Books", 169000, 2, [],
     "Các thí nghiệm cho thấy con người phi lý trí một cách có thể dự đoán được.", False),
    ("tam-ly-hoc", "Tâm Lý Học Đám Đông", "Gustave Le Bon", "NXB Thế Giới", "Alpha Books", 99000, 3, [],
     "Phân tích kinh điển về tâm lý và hành vi của con người khi hòa vào đám đông.", False),

    # --- Lịch sử ---
    ("lich-su", "Sapiens: Lược Sử Loài Người", "Yuval Noah Harari", "NXB Thế Giới", "Omega Plus", 299000, 6, [("Bìa cứng", 90000)],
     "Hành trình của loài người từ thời đồ đá đến cách mạng khoa học và những gì đã định hình chúng ta.", False),
    ("lich-su", "Homo Deus: Lược Sử Tương Lai", "Yuval Noah Harari", "NXB Thế Giới", "Omega Plus", 289000, 3, [],
     "Nhân loại sẽ theo đuổi điều gì khi đã phần nào chế ngự được nạn đói, dịch bệnh và chiến tranh.", False),
    ("lich-su", "21 Bài Học Cho Thế Kỷ 21", "Yuval Noah Harari", "NXB Thế Giới", "Omega Plus", 239000, 2, [],
     "Những vấn đề cấp bách của hiện tại: công nghệ, chính trị, sự thật và ý nghĩa cuộc sống.", False),
    ("lich-su", "Súng, Vi Trùng Và Thép", "Jared Diamond", "NXB Thế Giới", "Omega Plus", 268000, 2, [],
     "Vì sao các nền văn minh phát triển không đồng đều trên những lục địa khác nhau.", False),
    ("lich-su", "Việt Nam Sử Lược", "Trần Trọng Kim", "NXB Văn Học", "Đông A", 215000, 3, [("Bìa cứng", 80000)],
     "Bộ thông sử Việt Nam viết bằng quốc ngữ đầu tiên, từ thời Hồng Bàng đến thời Pháp thuộc.", False),
    ("lich-su", "Đại Việt Sử Ký Toàn Thư", "Ngô Sĩ Liên và các sử thần", "NXB Văn Học", "Đông A", 590000, 1, [],
     "Bộ chính sử quan trọng bậc nhất của Việt Nam, bản dịch trọn bộ đóng bìa cứng.", False),
    ("lich-su", "Lịch Sử Việt Nam Bằng Tranh - Tập 1", "Trần Bạch Đằng", "NXB Trẻ", "NXB Trẻ", 35000, 3, [],
     "Thời Hùng Vương dựng nước được kể lại bằng tranh, dễ đọc cho cả thiếu nhi.", False),

    # --- Khoa học ---
    ("khoa-hoc", "Lược Sử Thời Gian", "Stephen Hawking", "NXB Trẻ", "NXB Trẻ", 115000, 4, [],
     "Từ Vụ Nổ Lớn đến lỗ đen, những câu hỏi lớn về vũ trụ được giải thích cho người không chuyên.", False),
    ("khoa-hoc", "Vũ Trụ Trong Vỏ Hạt Dẻ", "Stephen Hawking", "NXB Trẻ", "NXB Trẻ", 135000, 2, [],
     "Những khám phá mới của vật lý lý thuyết, minh họa sinh động và dễ tiếp cận.", False),
    ("khoa-hoc", "Vũ Trụ", "Carl Sagan", "NXB Thế Giới", "Nhã Nam", 250000, 2, [],
     "Hành trình mười ba chương khám phá vũ trụ, sự sống và vị trí của con người trong đó.", False),
    ("khoa-hoc", "Gen: Lịch Sử Và Tương Lai Của Nhân Loại", "Siddhartha Mukherjee", "NXB Thế Giới", "Omega Plus", 345000, 1, [],
     "Lịch sử khoa học di truyền từ Mendel đến công nghệ chỉnh sửa gen.", False),
    ("khoa-hoc", "Nguồn Gốc Các Loài", "Charles Darwin", "NXB Thế Giới", "Omega Plus", 260000, 1, [],
     "Tác phẩm đặt nền móng cho thuyết tiến hóa bằng chọn lọc tự nhiên.", False),

    # --- Thiếu nhi ---
    ("thieu-nhi", "Dế Mèn Phiêu Lưu Ký", "Tô Hoài", "NXB Kim Đồng", "NXB Kim Đồng", 45000, 6, [("Bìa cứng", 55000)],
     "Cuộc phiêu lưu của chú Dế Mèn qua thế giới loài vật, tác phẩm thiếu nhi kinh điển của Việt Nam.", False),
    ("thieu-nhi", "Đất Rừng Phương Nam", "Đoàn Giỏi", "NXB Kim Đồng", "NXB Kim Đồng", 110000, 4, [],
     "Hành trình lưu lạc của bé An giữa thiên nhiên và con người vùng đất Nam Bộ.", False),
    ("thieu-nhi", "Totto-chan Bên Cửa Sổ", "Kuroyanagi Tetsuko", "NXB Hội Nhà Văn", "Nhã Nam", 98000, 5, [],
     "Cô bé Totto-chan và ngôi trường Tomoe đặc biệt với những toa tàu làm lớp học.", False),
    ("thieu-nhi", "Chuyện Con Mèo Dạy Hải Âu Bay", "Luis Sepúlveda", "NXB Hội Nhà Văn", "Nhã Nam", 55000, 4, [],
     "Chú mèo mun Zorba giữ lời hứa nuôi nấng và dạy một chú hải âu con biết bay.", False),
    ("thieu-nhi", "Kính Vạn Hoa - Tập 1", "Nguyễn Nhật Ánh", "NXB Kim Đồng", "NXB Kim Đồng", 75000, 3, [],
     "Những chuyện vui buồn của nhóm bạn Quý ròm, Tiểu Long và nhỏ Hạnh.", False),
    ("thieu-nhi", "Những Tấm Lòng Cao Cả", "Edmondo De Amicis", "NXB Kim Đồng", "NXB Kim Đồng", 85000, 3, [],
     "Nhật ký một năm học của cậu bé Enrico với những bài học về tình thương và lòng dũng cảm.", False),
    ("thieu-nhi", "Cổ Tích Việt Nam Chọn Lọc", "Nhiều tác giả", "NXB Kim Đồng", "NXB Kim Đồng", 120000, 3, [],
     "Tuyển tập truyện cổ tích quen thuộc có tranh minh họa màu.", False),
    ("thieu-nhi", "Charlie Và Nhà Máy Sô-cô-la", "Roald Dahl", "NXB Trẻ", "NXB Trẻ", 72000, 3, [],
     "Cậu bé Charlie nghèo khó may mắn có tấm vé vàng vào thăm nhà máy sô-cô-la kỳ diệu.", False),
    ("thieu-nhi", "Nhóc Nicolas: Những Chuyện Chưa Kể", "René Goscinny, Jean-Jacques Sempé", "NXB Hội Nhà Văn", "Nhã Nam", 89000, 2, [],
     "Những trò nghịch ngợm hài hước của cậu bé Nicolas cùng đám bạn ở trường.", False),
    ("thieu-nhi", "10 Vạn Câu Hỏi Vì Sao - Khoa Học Tự Nhiên", "Nhiều tác giả", "NXB Kim Đồng", "NXB Kim Đồng", 150000, 3, [],
     "Giải đáp những câu hỏi tò mò của trẻ về thiên nhiên, cơ thể và thế giới quanh ta.", False),

    # --- Truyện tranh ---
    ("truyen-tranh", "Doraemon Truyện Ngắn - Tập 1", "Fujiko F. Fujio", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 7, [],
     "Chú mèo máy đến từ thế kỷ 22 cùng những bảo bối giúp đỡ cậu bé Nobita.", False),
    ("truyen-tranh", "Doraemon Truyện Ngắn - Tập 2", "Fujiko F. Fujio", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 5, [],
     "Những câu chuyện tiếp theo của Doraemon, Nobita, Xuka, Chaien và Xêkô.", False),
    ("truyen-tranh", "Thám Tử Lừng Danh Conan - Tập 1", "Gosho Aoyama", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 6, [],
     "Thám tử trung học Kudo Shinichi bị teo nhỏ và bắt đầu cuộc sống mới với tên Edogawa Conan.", False),
    ("truyen-tranh", "Thám Tử Lừng Danh Conan - Tập 2", "Gosho Aoyama", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 4, [],
     "Conan tiếp tục phá án cùng Ran và thám tử Mori trong khi truy tìm Tổ chức Áo đen.", False),
    ("truyen-tranh", "One Piece - Tập 1", "Eiichiro Oda", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 5, [],
     "Monkey D. Luffy ra khơi với ước mơ tìm kho báu One Piece và trở thành Vua Hải Tặc.", False),
    ("truyen-tranh", "Naruto - Tập 1", "Masashi Kishimoto", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 3, [],
     "Cậu ninja tinh nghịch Naruto mang trong mình Cửu Vĩ và ước mơ trở thành Hokage.", False),
    ("truyen-tranh", "Dragon Ball - Tập 1", "Akira Toriyama", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 3, [],
     "Cậu bé có đuôi Son Goku cùng Bulma lên đường tìm bảy viên ngọc rồng.", False),
    ("truyen-tranh", "Shin - Cậu Bé Bút Chì - Tập 1", "Yoshito Usui", "NXB Kim Đồng", "NXB Kim Đồng", 25000, 3, [],
     "Cậu bé năm tuổi Shinnosuke với những trò quậy phá khiến cả nhà dở khóc dở cười.", False),
    ("truyen-tranh", "Thanh Gươm Diệt Quỷ - Tập 1", "Koyoharu Gotouge", "NXB Kim Đồng", "NXB Kim Đồng", 30000, 4, [],
     "Tanjiro trở thành kiếm sĩ diệt quỷ để cứu em gái Nezuko đã bị biến thành quỷ.", False),
    ("truyen-tranh", "Spy x Family - Tập 1", "Tatsuya Endo", "NXB Kim Đồng", "NXB Kim Đồng", 30000, 5, [("Bản đặc biệt", 20000)],
     "Điệp viên, sát thủ và cô bé đọc được suy nghĩ cùng sống trong một gia đình giả.", False),
    ("truyen-tranh", "Chú Thuật Hồi Chiến - Tập 1", "Gege Akutami", "NXB Kim Đồng", "NXB Kim Đồng", 30000, 4, [],
     "Itadori Yuji nuốt ngón tay của Sukuna và bước vào thế giới của các chú thuật sư.", True),
    ("truyen-tranh", "Thần Đồng Đất Việt - Tập 1", "Lê Linh", "NXB Trẻ", "NXB Trẻ", 18000, 2, [],
     "Trạng Tí và những người bạn với các câu chuyện dí dỏm mang đậm văn hóa Việt.", False),

    # --- Ngoại ngữ ---
    ("ngoai-ngu", "Ngữ Pháp Tiếng Anh", "Mai Lan Hương, Hà Thanh Uyên", "NXB Đà Nẵng", "MCBooks", 98000, 4, [],
     "Tổng hợp ngữ pháp tiếng Anh từ cơ bản đến nâng cao kèm bài tập có đáp án.", False),
    ("ngoai-ngu", "600 Essential Words For The TOEIC", "Lin Lougheed", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 180000, 3, [],
     "Sáu trăm từ vựng thiết yếu theo chủ đề thường gặp trong đề thi TOEIC.", False),
    ("ngoai-ngu", "Cambridge IELTS 19 Academic", "Cambridge University Press", "NXB Tổng hợp TP.HCM", "First News - Trí Việt", 165000, 4, [],
     "Bốn đề thi IELTS Academic chính thức kèm đáp án và file nghe.", True),
    ("ngoai-ngu", "Hackers IELTS Basic Listening", "Hackers Language Research Institute", "NXB Tổng hợp TP.HCM", "MCBooks", 189000, 3, [],
     "Lộ trình luyện nghe IELTS cho người mới bắt đầu, chia theo dạng câu hỏi.", False),
    ("ngoai-ngu", "Minna No Nihongo Sơ Cấp 1 - Bản Tiếng Nhật", "3A Corporation", "NXB Trẻ", "NXB Trẻ", 128000, 3, [],
     "Giáo trình tiếng Nhật sơ cấp phổ biến nhất, 25 bài học đầu tiên.", False),
    ("ngoai-ngu", "Giáo Trình Hán Ngữ - Tập 1", "Dương Ký Châu", "NXB ĐHQG Hà Nội", "MCBooks", 98000, 3, [],
     "Giáo trình tiếng Trung cơ bản dành cho người mới học, phiên bản mới.", False),
    ("ngoai-ngu", "Tự Học Tiếng Hàn Cho Người Mới Bắt Đầu", "Nhiều tác giả", "NXB Hồng Đức", "MCBooks", 119000, 2, [],
     "Bảng chữ cái Hangeul, phát âm và hội thoại thông dụng có file nghe kèm theo.", False),
]

# Sách đã có sẵn từ seed.sql (SKU sản phẩm -> nhà cung cấp, độ phổ biến),
# đưa vào mô phỏng bán hàng nếu tồn tại trong DB.
EXISTING_PRODUCTS = {
    "SACH-001": ("Đông A", 3),
    "SACH-002": ("Nhã Nam", 8),
}

# ---------------------------------------------------------------------------
# Tên người Việt
# ---------------------------------------------------------------------------
SURNAMES = [
    ("Nguyễn", 31), ("Trần", 11), ("Lê", 9), ("Phạm", 7), ("Hoàng", 5), ("Huỳnh", 4),
    ("Phan", 4), ("Vũ", 4), ("Võ", 4), ("Đặng", 3), ("Bùi", 3), ("Đỗ", 3), ("Hồ", 2),
    ("Ngô", 2), ("Dương", 2), ("Lý", 1), ("Trịnh", 1), ("Đinh", 1), ("Mai", 1),
    ("Lâm", 1), ("Trương", 1), ("Cao", 1),
]
MIDDLE_MALE = ["Văn", "Đức", "Minh", "Quang", "Hoàng", "Thanh", "Hữu", "Công", "Tuấn", "Gia", "Anh", "Xuân", "Trọng", "Nhật"]
MIDDLE_FEMALE = ["Thị", "Ngọc", "Thu", "Thanh", "Thùy", "Phương", "Mai", "Bảo", "Khánh", "Hồng", "Minh", "Diệu", "Hải"]
GIVEN_MALE = ["Anh", "Bảo", "Cường", "Dũng", "Duy", "Đạt", "Hải", "Hiếu", "Hùng", "Huy", "Khang", "Khoa",
              "Kiên", "Long", "Lâm", "Minh", "Nam", "Nghĩa", "Phong", "Phúc", "Quân", "Sơn", "Tài",
              "Thắng", "Thành", "Tiến", "Trung", "Tùng", "Việt", "Vinh"]
GIVEN_FEMALE = ["An", "Anh", "Chi", "Diệp", "Dung", "Giang", "Hà", "Hân", "Hằng", "Hoa", "Hương", "Huyền",
                "Lan", "Linh", "Ly", "Mai", "My", "Ngân", "Ngọc", "Nhi", "Nhung", "Phương", "Quỳnh",
                "Thảo", "Thư", "Trang", "Trinh", "Uyên", "Vy", "Yến"]

# Đầu số di động Việt Nam (Viettel, Vinaphone, MobiFone, Vietnamobile)
PHONE_PREFIXES = ["032", "033", "034", "035", "036", "037", "038", "039", "086", "096", "097", "098",
                  "081", "082", "083", "084", "085", "088", "091", "094",
                  "070", "076", "077", "078", "079", "089", "090", "093", "056", "058"]

# Tên miền dành riêng cho tài liệu/ví dụ (RFC 2606): trông như email thật nhưng
# không bao giờ gửi tới hộp thư của người thật, kể cả khi cấu hình SMTP thật.
EMAIL_DOMAINS = ["example.com", "example.com", "example.com", "example.net", "example.org"]

STAFF = [
    # (họ tên, email, điện thoại, đang hoạt động?)
    ("Trần Thị Thu Hà", "ha.tran@tbookstore.vn", "0912345601", True),
    ("Lê Minh Tuấn", "tuan.le@tbookstore.vn", "0912345602", True),
    ("Phạm Ngọc Ánh", "anh.pham@tbookstore.vn", "0912345603", True),
    ("Võ Quốc Bảo", "bao.vo@tbookstore.vn", "0912345604", False),  # đã nghỉ việc, tài khoản bị khóa
]

# ---------------------------------------------------------------------------
# Địa chỉ: tỉnh/thành -> (trọng số, [phường/xã], [đường], [tòa nhà/chung cư], nội thành lớn?)
# ---------------------------------------------------------------------------
PROVINCES = {
    "TP. Hồ Chí Minh": (36,
        ["Phường Sài Gòn", "Phường Bến Thành", "Phường Tân Định", "Phường Cầu Ông Lãnh", "Phường Bàn Cờ",
         "Phường Xuân Hòa", "Phường Nhiêu Lộc", "Phường Phú Nhuận", "Phường Gia Định", "Phường Bình Thạnh",
         "Phường Thạnh Mỹ Tây", "Phường Tân Sơn Nhất", "Phường Gò Vấp", "Phường Hạnh Thông", "Phường Thủ Đức",
         "Phường Linh Xuân", "Phường An Khánh", "Phường Tân Mỹ", "Phường Chợ Lớn", "Phường Phú Lâm",
         "Phường Thủ Dầu Một", "Phường Dĩ An", "Phường Vũng Tàu"],
        ["Nguyễn Thị Minh Khai", "Lê Lợi", "Điện Biên Phủ", "Cách Mạng Tháng Tám", "Võ Văn Tần",
         "Nguyễn Đình Chiểu", "Phan Xích Long", "Hoàng Văn Thụ", "Nguyễn Văn Linh", "Võ Văn Ngân",
         "Kha Vạn Cân", "Quang Trung", "Phan Văn Trị", "Lý Thường Kiệt", "Ba Tháng Hai", "Nguyễn Trãi",
         "Xô Viết Nghệ Tĩnh", "Lê Văn Sỹ", "Trường Chinh", "Phạm Văn Đồng"],
        ["Vinhomes Central Park", "Vinhomes Grand Park", "Masteri Thảo Điền", "Sunrise City", "The Sun Avenue"],
        True),
    "Hà Nội": (30,
        ["Phường Hoàn Kiếm", "Phường Cửa Nam", "Phường Ba Đình", "Phường Ngọc Hà", "Phường Giảng Võ",
         "Phường Hai Bà Trưng", "Phường Bạch Mai", "Phường Đống Đa", "Phường Láng", "Phường Kim Liên",
         "Phường Văn Miếu - Quốc Tử Giám", "Phường Cầu Giấy", "Phường Nghĩa Đô", "Phường Yên Hòa",
         "Phường Thanh Xuân", "Phường Khương Đình", "Phường Hoàng Mai", "Phường Long Biên", "Phường Tây Hồ",
         "Phường Hà Đông", "Phường Từ Liêm", "Phường Xuân Phương"],
        ["Xuân Thủy", "Cầu Giấy", "Trần Duy Hưng", "Nguyễn Trãi", "Láng Hạ", "Kim Mã", "Đội Cấn",
         "Hoàng Quốc Việt", "Chùa Bộc", "Phố Huế", "Bạch Mai", "Tôn Đức Thắng", "Nguyễn Chí Thanh",
         "Lê Văn Lương", "Giải Phóng", "Nguyễn Văn Cừ", "Lạc Long Quân", "Hồ Tùng Mậu", "Phạm Hùng"],
        ["Times City", "Royal City", "Vinhomes Ocean Park", "Vinhomes Smart City", "Goldmark City"],
        True),
    "Đà Nẵng": (7,
        ["Phường Hải Châu", "Phường Thanh Khê", "Phường Sơn Trà", "Phường An Hải", "Phường Ngũ Hành Sơn",
         "Phường Hòa Cường", "Phường Hội An"],
        ["Nguyễn Văn Linh", "Lê Duẩn", "Hùng Vương", "Bạch Đằng", "Võ Nguyên Giáp", "Hoàng Diệu", "Nguyễn Tri Phương"],
        [], False),
    "Hải Phòng": (5,
        ["Phường Hồng Bàng", "Phường Lê Chân", "Phường Ngô Quyền", "Phường Hải An", "Phường Kiến An", "Phường Hải Dương"],
        ["Lạch Tray", "Điện Biên Phủ", "Trần Phú", "Lê Lợi", "Tô Hiệu", "Văn Cao"], [], False),
    "Cần Thơ": (4,
        ["Phường Ninh Kiều", "Phường Cái Khế", "Phường Tân An", "Phường Bình Thủy"],
        ["30 Tháng 4", "Nguyễn Văn Cừ", "Trần Hưng Đạo", "Mậu Thân", "Hòa Bình"], [], False),
    "Huế": (3,
        ["Phường Thuận Hóa", "Phường Phú Xuân", "Phường Kim Long", "Phường Vỹ Dạ"],
        ["Lê Lợi", "Hùng Vương", "Nguyễn Huệ", "Bà Triệu"], [], False),
    "Khánh Hòa": (3,
        ["Phường Nha Trang", "Phường Bắc Nha Trang", "Phường Nam Nha Trang"],
        ["Trần Phú", "Yersin", "Thái Nguyên", "23 Tháng 10"], [], False),
    "Nghệ An": (3,
        ["Phường Thành Vinh", "Phường Trường Vinh", "Phường Vinh Hưng"],
        ["Lê Lợi", "Quang Trung", "Nguyễn Văn Cừ", "Lê Duẩn"], [], False),
    "Đồng Nai": (3,
        ["Phường Biên Hòa", "Phường Trấn Biên", "Phường Tam Hiệp"],
        ["Phạm Văn Thuận", "Đồng Khởi", "Võ Thị Sáu"], [], False),
    "Bắc Ninh": (3,
        ["Phường Kinh Bắc", "Phường Võ Cường", "Phường Bắc Giang"],
        ["Lý Thái Tổ", "Nguyễn Gia Thiều", "Trần Hưng Đạo"], [], False),
    "Quảng Ninh": (2,
        ["Phường Hạ Long", "Phường Bãi Cháy", "Phường Hồng Gai"],
        ["Hạ Long", "Cao Thắng", "Nguyễn Văn Cừ"], [], False),
    "Lâm Đồng": (1,
        ["Phường Xuân Hương - Đà Lạt", "Phường Lâm Viên - Đà Lạt"],
        ["Phan Đình Phùng", "Ba Tháng Hai", "Trần Hưng Đạo"], [], False),
}

OFFICE_BUILDINGS = {
    "TP. Hồ Chí Minh": ["Bitexco Financial Tower", "Saigon Centre", "Etown Cộng Hòa", "Viettel Complex"],
    "Hà Nội": ["Keangnam Landmark 72", "Lotte Center", "Capital Place", "Toà nhà Handico"],
}

CARRIERS = ["GHN", "GHTK", "Viettel Post", "J&T Express", "Ninja Van"]

# ---------------------------------------------------------------------------
# Hủy đơn / hoàn tiền / đánh giá
# ---------------------------------------------------------------------------
CUSTOMER_CANCEL_NOTES = [
    "Khách đặt nhầm phiên bản bìa",
    "Khách muốn đổi địa chỉ giao hàng, sẽ đặt lại đơn mới",
    "Khách đổi ý, không mua nữa",
    "Khách tìm được chỗ khác giao nhanh hơn",
    "Khách muốn thêm sách vào đơn nên hủy để đặt lại",
]
STAFF_CANCEL_NOTES = [
    "Gọi 3 lần không liên lạc được khách để xác nhận đơn COD",
    "Khách từ chối nhận cuộc gọi xác nhận, nghi đơn ảo",
    "Địa chỉ giao hàng không đầy đủ, khách không phản hồi",
]
PAYMENT_FAIL_CANCEL_NOTE = "Hủy do thanh toán online không thành công quá 24 giờ"

REFUND_REASONS = [
    ("Sách bị rách bìa và gãy gáy khi nhận hàng", "item"),
    ("Giao sai phiên bản: đặt bìa cứng nhưng nhận bìa mềm", "item"),
    ("Sách bị ẩm, ố vàng nhiều trang", "item"),
    ("Thiếu một cuốn so với đơn đặt hàng", "item"),
    ("In lỗi, mất khoảng 16 trang ở giữa sách", "item"),
    ("Đơn giao trễ hơn 10 ngày, không còn nhu cầu", "full"),
    ("Nhận được sách đã qua sử dụng, có vết viết bút", "item"),
]

REVIEW_COMMENTS = {
    5: [
        "Sách đẹp, giấy dày, đóng gói rất kỹ. Sẽ ủng hộ shop tiếp.",
        "Nội dung hay, đọc một mạch hết luôn. Giao hàng nhanh.",
        "Mua tặng bạn mà bạn thích lắm, bìa đẹp hơn trong ảnh.",
        "Đọc lần thứ hai vẫn thấy hay. Shop bọc sách cẩn thận.",
        "Hàng chính hãng, có tem. Giao 2 ngày là nhận.",
        "Rất đáng tiền, nên có trong tủ sách.",
        "Bản dịch mượt, dễ đọc. 10 điểm.",
        "Đóng hộp cứng, không móp méo gì. Cảm ơn shop!",
        "Đợi flash sale mới mua, giá quá hời.",
    ],
    4: [
        "Sách hay, nhưng bìa hơi trầy nhẹ ở góc.",
        "Nội dung tốt, giao hơi chậm một chút.",
        "Giấy ổn, chữ in rõ. Trừ 1 sao vì đóng gói hơi sơ sài.",
        "Đọc cuốn hút, phần cuối hơi dài dòng.",
        "Giá hợp lý, chất lượng tốt so với tiền.",
        "Ok, đúng mô tả. Lần sau mong shop bọc màng co.",
    ],
    3: [
        "Nội dung bình thường, không như kỳ vọng.",
        "Giấy hơi mỏng, nhìn xuyên chữ trang sau.",
        "Giao hàng chậm gần một tuần.",
        "Sách ổn nhưng có vài lỗi chính tả.",
    ],
    2: [
        "Bìa bị móp do đóng gói không kỹ.",
        "Bản dịch khó đọc, nhiều câu lủng củng.",
        "Sách có mùi ẩm, chắc để kho lâu.",
    ],
    1: [
        "Nhận sách bị rách mấy trang, rất thất vọng.",
        "Giao sai sách, liên hệ mãi mới được hỗ trợ.",
        "Chất lượng in quá tệ, chữ bị nhòe.",
    ],
}
CATEGORY_REVIEW_COMMENTS = {
    "thieu-nhi": ["Bé nhà mình mê lắm, tối nào cũng đòi đọc.", "Tranh minh họa màu đẹp, bé 6 tuổi đọc được."],
    "truyen-tranh": ["Mua đủ bộ cho em trai, giao đủ không thiếu tập nào.", "Giấy in truyện tranh đẹp, không lem."],
    "ngoai-ngu": ["Có kèm mã QR nghe audio, rất tiện.", "Học được 2 tuần thấy tiến bộ rõ."],
    "kinh-te": ["Kiến thức thực tế, áp dụng được vào công việc.", "Nên đọc chậm và ghi chép lại."],
    "ky-nang-song": ["Đọc xong thay đổi suy nghĩ nhiều thứ.", "Sách mỏng, dễ đọc, hợp mang theo đi làm."],
    "trinh-tham": ["Cú twist cuối truyện quá đỉnh.", "Đọc đến 2 giờ sáng vì không dứt ra được."],
}
SPAM_REVIEW = "Shop uy tín. Ai cần mua sách giá sỉ liên hệ zalo trong trang cá nhân nhé!!!"
