# Banka Uygulaması (C)

Basit bir **terminal tabanlı banka sistemi**. Uygulama C dili ile yazılmıştır ve kullanıcı hesaplarını dosyaya kaydederek sonraki çalıştırmalarda verileri geri yükler.

## Özellikler

- Hesap oluşturma (benzersiz kullanıcı adı)
- Giriş yapma (kullanıcı adı + şifre)
- Bakiye görüntüleme
- Para yatırma
- Para çekme
- Başka kullanıcıya para transferi
- Hesap verilerinin `accounts.txt` dosyasına kalıcı olarak kaydedilmesi

## Proje Yapısı

- `main.c`: Uygulamanın tüm kaynak kodu
- `accounts.txt`: Çalışma sırasında otomatik oluşan/veri saklayan dosya

## Gereksinimler

- C derleyicisi (GCC önerilir)
- Windows ortamı (kodda `windows.h` ve `cls` kullanımı vardır)

> Not: Linux/macOS üzerinde çalıştırmak için `#include "windows.h"` satırını kaldırmanız ve `system("cls")` yerine örneğin `system("clear")` kullanmanız gerekir.

## Derleme ve Çalıştırma

### MinGW/GCC (Windows)

```bash
gcc main.c -o banka_uygulamasi
banka_uygulamasi.exe
```

## Kullanım Akışı

Program açıldığında ana menü gelir:

1. **Hesap Oluştur**
2. **Giriş Yap**
3. **Çıkış**

Giriş yaptıktan sonra hesap menüsü:

1. **Bakiye Görüntüle**
2. **Para Yatır**
3. **Para Çek**
4. **Para Transfer Et**
5. **Çıkış Yap**

## Veri Saklama

Uygulama hesapları düz metin olarak `accounts.txt` dosyasında saklar. Program her açılışta bu dosyayı okuyarak hesapları yükler, işlem sonrası dosyayı günceller.

## Bilinen Kısıtlar

- Maksimum hesap sayısı: `100`
- Şifreler düz metin olarak saklanır (güvenli değildir; öğrenme amaçlıdır)
- Giriş doğrulaması ve kullanıcı etkileşimi temel seviyededir

## Geliştirme Fikirleri

- Şifreleri hashleyerek saklama
- İşlem geçmişi (log) ekleme
- Daha güvenli ve dayanıklı dosya/parsing yapısı
- Platform bağımsız terminal temizleme yöntemi
- Menü ve girişlerde daha güçlü hata yakalama
