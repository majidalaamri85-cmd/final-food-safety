from django.core.management.base import BaseCommand

from inspections.models import Governorate, Wilayat


OMAN_LOCATIONS = {
    'مسقط': {
        'en': 'Muscat',
        'wilayats': [
            ('مسقط', 'Muscat'),
            ('مطرح', 'Muttrah'),
            ('السيب', 'As Seeb'),
            ('بوشر', 'Bausher'),
            ('العامرات', 'Al Amerat'),
            ('قريات', 'Qurayyat'),
        ],
    },
    'ظفار': {
        'en': 'Dhofar',
        'wilayats': [
            ('صلالة', 'Salalah'),
            ('طاقة', 'Taqah'),
            ('مرباط', 'Mirbat'),
            ('رخيوت', 'Rakhyut'),
            ('ثمريت', 'Thumrait'),
            ('ضلكوت', 'Dhalqut'),
            ('المزيونة', 'Al Mazyonah'),
            ('مقشن', 'Muqshin'),
            ('شليم وجزر الحلانيات', 'Shalim and the Hallaniyat Islands'),
            ('سدح', 'Sadah'),
        ],
    },
    'مسندم': {
        'en': 'Musandam',
        'wilayats': [
            ('خصب', 'Khasab'),
            ('دبا', 'Dibba'),
            ('بخا', 'Bukha'),
            ('مدحاء', 'Madha'),
        ],
    },
    'البريمي': {
        'en': 'Al Buraimi',
        'wilayats': [
            ('البريمي', 'Al Buraimi'),
            ('محضة', 'Mahdah'),
            ('السنينة', 'As Sunaynah'),
        ],
    },
    'شمال الباطنة': {
        'en': 'North Al Batinah',
        'wilayats': [
            ('صحار', 'Sohar'),
            ('شناص', 'Shinas'),
            ('لوى', 'Liwa'),
            ('صحم', 'Saham'),
            ('الخابورة', 'Al Khaburah'),
            ('السويق', 'As Suwaiq'),
        ],
    },
    'جنوب الباطنة': {
        'en': 'South Al Batinah',
        'wilayats': [
            ('الرستاق', 'Ar Rustaq'),
            ('العوابي', 'Al Awabi'),
            ('نخل', 'Nakhal'),
            ('وادي المعاول', 'Wadi Al Maawil'),
            ('بركاء', 'Barka'),
            ('المصنعة', 'Al Musannah'),
        ],
    },
    'الداخلية': {
        'en': 'Ad Dakhiliyah',
        'wilayats': [
            ('نزوى', 'Nizwa'),
            ('بهلاء', 'Bahla'),
            ('منح', 'Manah'),
            ('الحمراء', 'Al Hamra'),
            ('أدم', 'Adam'),
            ('إزكي', 'Izki'),
            ('سمائل', 'Samail'),
            ('بدبد', 'Bidbid'),
        ],
    },
    'شمال الشرقية': {
        'en': 'North Ash Sharqiyah',
        'wilayats': [
            ('إبراء', 'Ibra'),
            ('المضيبي', 'Al Mudhaibi'),
            ('بدية', 'Bidiyah'),
            ('القابل', 'Al Qabil'),
            ('وادي بني خالد', 'Wadi Bani Khalid'),
            ('دماء والطائيين', 'Dima Wa Al Tayeen'),
        ],
    },
    'جنوب الشرقية': {
        'en': 'South Ash Sharqiyah',
        'wilayats': [
            ('صور', 'Sur'),
            ('الكامل والوافي', 'Al Kamil Wal Wafi'),
            ('جعلان بني بو حسن', 'Jalan Bani Bu Hassan'),
            ('جعلان بني بو علي', 'Jalan Bani Bu Ali'),
            ('مصيرة', 'Masirah'),
        ],
    },
    'الظاهرة': {
        'en': 'Az Zahirah',
        'wilayats': [
            ('عبري', 'Ibri'),
            ('ينقل', 'Yanqul'),
            ('ضنك', 'Dhank'),
        ],
    },
    'الوسطى': {
        'en': 'Al Wusta',
        'wilayats': [
            ('هيما', 'Haima'),
            ('محوت', 'Mahout'),
            ('الدقم', 'Duqm'),
            ('الجازر', 'Al Jazer'),
        ],
    },
}


class Command(BaseCommand):
    help = 'تحميل محافظات وولايات سلطنة عُمان الرسمية'

    def handle(self, *args, **options):
        for governorate_name_ar, governorate_data in OMAN_LOCATIONS.items():
            governorate, _ = Governorate.objects.update_or_create(
                name_ar=governorate_name_ar,
                defaults={'name_en': governorate_data['en']},
            )
            for wilayat_name_ar, wilayat_name_en in governorate_data['wilayats']:
                Wilayat.objects.update_or_create(
                    governorate=governorate,
                    name_ar=wilayat_name_ar,
                    defaults={'name_en': wilayat_name_en},
                )

        self.stdout.write('تم تحميل جميع المحافظات والولايات بنجاح.')
