# isobed18/kantinyonetim/kantinyonetim-mobile_app/kantinyonetim/apps/menu/management/commands/populate_menu.py

import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from apps.menu.models import MenuItem
from apps.stock.models import Stock

# Genişletilmiş ve URL'leri doğrulanmış yeni menü listesi
MENU_DATA = [
    {
        'name': 'Çay',
        'description': 'Taze demlenmiş, klasik Türk çayı.',
        'price': 15.00,
        'category': 'icecek',
        'image_url': 'https://www.alamy.com/stock-photo-turkish-tea-cay-served-in-tulip-shaped-glass-54239872.html'
    },
    {
        'name': 'Türk Kahvesi',
        'description': 'Bol köpüklü, geleneksel lezzet.',
        'price': 40.00,
        'category': 'icecek',
        'image_url': 'https://sakiproducts.com/cdn/shop/articles/What-is-Turkish-Coffee-Thumbnail_62130558-e5da-432c-9baf-4298ab3f97c0_640x640.jpg?v=1749818984'
    },
    {
        'name': 'Nescafe 3\'ü 1 arada',
        'description': 'Granül nesacafe üçü bir arada',
        'price': 20.00,
        'category': 'icecek',
        'image_url' : 'https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.migros.com.tr%2Fnescafe-3u-1-arada-original-175-g-p-312b30%3Fsrsltid%3DAfmBOoplZf3kB4GY13Q_xjCFzm0ZmXE--FXyhTZc3lHxiVVi1bfRVEYP&psig=AOvVaw0WoB7J9NFNRkx6cC_xxuiH&ust=1756201878687000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCLC4g_zXpY8DFQAAAAAdAAAAABAE'
    },
    {
        'name': 'Nescafe 2\'si 1 arada',
        'description': 'Nescafe 2si 1 arada',
        'price': 20.00,
        'category': 'icecek',
        'image_url' : 'https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.migros.com.tr%2Fnescafe-3u-1-arada-original-175-g-p-312b30%3Fsrsltid%3DAfmBOoplZf3kB4GY13Q_xjCFzm0ZmXE--FXyhTZc3lHxiVVi1bfRVEYP&psig=AOvVaw0WoB7J9NFNRkx6cC_xxuiH&ust=1756201878687000&source=images&cd=vfe&opi=89978449&ved=0CBUQjRxqFwoTCLC4g_zXpY8DFQAAAAAdAAAAABAE'
    },
    {
        'name': 'Ayran',
        'description': 'Serinletici ve sağlıklı, doğal ayran.',
        'price': 25.00,
        'category': 'icecek',
        'image_url': 'https://sifirbirkebap.com.tr/wp-content/uploads/2023/07/ayran.webp'
    },
    {
        'name': 'Kutu Kola',
        'description': 'Soğuk servis edilir.',
        'price': 40.00,
        'category': 'icecek',
        'image_url': 'https://cdn.dsmcdn.com/ty1442/product/media/images/prod/QC/20240725/20/a1345a89-b33d-354b-ab4e-b4a03a9570bf/1_org_zoom.jpg'
    },
    {
        'name': 'Ev Yapımı Limonata',
        'description': 'Nane ferahlığıyla hazırlanmış ev yapımı limonata.',
        'price': 55.00,
        'category': 'icecek',
        'image_url': 'https://i.lezzet.com.tr/images-xxlarge-recipe/ev-yapimi-konsantre-limonata-01e50b99-5890-411f-a4c2-997a71e8a5cc.jpg'
    },
    {
        'name': 'Tavuk Döner Dürüm',
        'description': 'Özel soslu tavuk döner, taze yeşilliklerle.',
        'price': 130.00,
        'category': 'ana_yemek',
        'image_url': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTB34PY9hlp5Us2g7SxZ5AMPLzj3cT312M96w&s'
    },
    {
        'name': 'Hamburger',
        'description': '120gr dana köftesi, turşu ve özel sos ile.',
        'price': 190.00,
        'category': 'ana_yemek',
        'image_url': 'https://www.washingtonpost.com/wp-apps/imrs.php?src=https://arc-anglerfish-washpost-prod-washpost.s3.amazonaws.com/public/M6HASPARCZHYNN4XTUYT7H6PTE.jpg&w=800&h=600'
    },
    {
        'name': 'Karışık Pizza',
        'description': 'Sucuk, salam, sosis, mısır ve zeytin.',
        'price': 220.00,
        'category': 'ana_yemek',
        'image_url': 'https://www.unileverfoodsolutions.com.tr/dam/global-ufs/mcos/TURKEY/calcmenu/recipes/TR-recipes/desserts-&-bakery/kar%C4%B1%C5%9F%C4%B1k-pizza/main-header.jpg'
    },
    {
        'name': 'Mercimek Çorbası',
        'description': 'Limon ve pul biber ile servis edilir.',
        'price': 60.00,
        'category': 'ana_yemek',
        'image_url': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRLvwsMnTe3X8DBGIIWw7M-rAlf19osq1CJOQ&s'
    },
    {
        'name': 'Menemen',
        'description': 'Soğanlı veya soğansız seçeneğiyle, taze domates ve biberle.',
        'price': 95.00,
        'category': 'ana_yemek',
        'image_url': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTVwnH__ahcV61-A4FvdyWdF_qPD5mgvmzpoQ&s'
    },
    {
        'name': 'Sandviç',

        'description' : 'Kaşarlı, salamlı klasik sandviç',
        'price' : 70.00,
        'category': 'aperatif',
        'image_url' : 'https://recipesblob.droetker.com.tr/assets/1146fbea6e7d4076879082bf89521e30/750x910/jambonlu-peynirli-soguk-sandvic.jpg'
    },
    {
        'name': 'Patates Kızartması',
        'description': 'Çıtır çıtır, bol porsiyon.',
        'price': 70.00,
        'category': 'aperatif',
        'image_url': 'https://i.lezzet.com.tr/images-xxlarge/unlu-patates-kizartmasi-e2cb5b2e-e67b-44ca-8492-7a4d29a88a95'
    },
    {
        'name': 'Karışık Tost',
        'description': 'Kaşar ve sucuk bir arada.',
        'price': 80.00,
        'category': 'aperatif',
        'image_url': 'https://i.lezzet.com.tr/images-800x600/sahur-icin-tost-tarifleri--bs64-605bb451-7abb-4828-80ce-4ce239ac7c7e'
    },
    {
        'name': 'Simit',
        'description': 'Taze ve sıcak, sokak simidi.',
        'price': 20.00,
        'category': 'aperatif',
        'image_url': 'https://turkishfoodie.com/wp-content/uploads/2018/07/Simit.jpg'
    },
    {
        'name': 'Fırın Sütlaç',
        'description': 'Üzeri nar gibi kızarmış, ev yapımı.',
        'price': 75.00,
        'category': 'tatli',
        'image_url': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQAbdoQuoZaBzkmYEzGWExUoO43q_G2WN3Ifg&s'
    },
    {
        'name': 'Brownie',
        'description': 'Yoğun çikolatalı ve ıslak.',
        'price': 85.00,
        'category': 'tatli',
        'image_url': 'https://images.migrosone.com/sanalmarket/product/05104002/5104002-63284f-1650x1650.jpg'
    },
    
    
]



class Command(BaseCommand):
    help = 'Populates the database with a predefined set of menu items and their stock.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Mevcut menü ve stok verileri siliniyor...'))
        MenuItem.objects.all().delete()
        Stock.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Mevcut veriler başarıyla silindi.'))

        media_path = os.path.join(settings.MEDIA_ROOT, 'menu_images')
        os.makedirs(media_path, exist_ok=True)

        for item_data in MENU_DATA:
            self.stdout.write(f"'{item_data['name']}' ekleniyor...")
            
            try:
                menu_item = MenuItem(
                    name=item_data['name'],
                    description=item_data['description'],
                    price=item_data['price'],
                    category=item_data['category'],
                    is_available=True
                )

                if item_data.get('image_url') and 'BURAYA' not in item_data['image_url']:
                    try:
                        response = requests.get(item_data['image_url'], stream=True, timeout=10)
                        response.raise_for_status()
                        
                        file_name = f"{item_data['name'].lower().replace(' ', '_').replace('ı', 'i').replace('ü', 'u').replace('ş', 's').replace('ç', 'c').replace('ğ', 'g').replace('ö', 'o')}.jpg"
                        menu_item.image.save(file_name, ContentFile(response.content), save=True)
                    
                    except requests.exceptions.RequestException as e:
                        self.stdout.write(self.style.ERROR(f"'{item_data['name']}' için resim indirilemedi. Hata: {e}"))
                
                menu_item.save()

                Stock.objects.create(menu_item=menu_item, quantity=50)

                self.stdout.write(self.style.SUCCESS(f"'{item_data['name']}' başarıyla eklendi."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"'{item_data['name']}' eklenirken bir hata oluştu: {e}"))

        self.stdout.write(self.style.SUCCESS('Veritabanı başarıyla dolduruldu!'))