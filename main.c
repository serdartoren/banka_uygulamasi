#include <stdio.h>
#include <string.h>
#include "windows.h"

#define MAX_ACCOUNT 100
#define DATA_FILE "accounts.txt"

typedef struct
{
    int id;
    char username[32];
    char password[32];
    float balance;
} Account_t;

Account_t accounts[MAX_ACCOUNT];
int account_count = 0;
int next_id = 1;

void save_accounts(void)
{
    FILE *fp = fopen(DATA_FILE, "w");

    if (fp == NULL)
    {
        printf("Dosya kaydedilemedi!\n");
        return;
    }

    fprintf(fp, "%d %d\n", account_count, next_id);

    for (int i = 0; i < account_count; i++)
    {
        fprintf(fp, "%d %s %s %.2f\n",
                accounts[i].id,
                accounts[i].username,
                accounts[i].password,
                accounts[i].balance);
    }

    fclose(fp);
}

void load_accounts(void)
{
    FILE *fp = fopen(DATA_FILE, "r");

    if (fp == NULL)
        return;

    fscanf(fp, "%d %d", &account_count, &next_id);

    for (int i = 0; i < account_count; i++)
    {
        fscanf(fp, "%d %s %s %f",
               &accounts[i].id,
               accounts[i].username,
               accounts[i].password,
               &accounts[i].balance);
    }

    fclose(fp);
}

int find_account_by_username(char username[])
{
    for (int i = 0; i < account_count; i++)
    {
        if (strcmp(accounts[i].username, username) == 0)
            return i;
    }

    return -1;
}

void create_account(void)
{
    if (account_count >= MAX_ACCOUNT)
    {
        printf("Maksimum hesap sayisina ulasildi!\n");
        return;
    }

    Account_t acc;

    acc.id = next_id++;
    acc.balance = 0;

    printf("Kullanici adi: ");
    scanf("%31s", acc.username);

    if (find_account_by_username(acc.username) != -1)
    {
        printf("Bu kullanici adi zaten var!\n");
        return;
    }

    printf("Sifre: ");
    scanf("%31s", acc.password);

    accounts[account_count++] = acc;
    save_accounts();

    printf("Hesap olusturuldu. Hesap ID: %d\n", acc.id);
}

int login(void)
{
    char username[32];
    char password[32];

    printf("Kullanici adi: ");
    scanf("%31s", username);

    printf("Sifre: ");
    scanf("%31s", password);

    int index = find_account_by_username(username);

    if (index == -1)
    {
        printf("Kullanici bulunamadi!\n");
        return -1;
    }

    if (strcmp(accounts[index].password, password) != 0)
    {
        printf("Sifre hatali!\n");
        return -1;
    }

    printf("Giris basarili. Hos geldin %s\n", accounts[index].username);
    return index;
}

void deposit(Account_t *acc)
{
    float amount;

    printf("Yatirilacak miktar: ");
    scanf("%f", &amount);

    if (amount <= 0)
    {
        printf("Gecersiz miktar!\n");
        return;
    }

    acc->balance += amount;
    save_accounts();

    printf("Para yatirildi. Yeni bakiye: %.2f TL\n", acc->balance);
}

void withdraw(Account_t *acc)
{
    float amount;

    printf("Cekilecek miktar: ");
    scanf("%f", &amount);

    if (amount <= 0)
    {
        printf("Gecersiz miktar!\n");
        return;
    }

    if (amount > acc->balance)
    {
        printf("Yetersiz bakiye!\n");
        return;
    }

    acc->balance -= amount;
    save_accounts();

    printf("Para cekildi. Yeni bakiye: %.2f TL\n", acc->balance);
}

void show_balance(Account_t *acc)
{
    printf("Bakiyeniz: %.2f TL\n", acc->balance);
}

void transfer(Account_t *sender)
{
    char target_username[32];
    float amount;

    printf("Alici kullanici adi: ");
    scanf("%31s", target_username);

    int target_index = find_account_by_username(target_username);

    if (target_index == -1)
    {
        printf("Alici bulunamadi!\n");
        return;
    }

    if (strcmp(sender->username, target_username) == 0)
    {
        printf("Kendinize para gonderemezsiniz!\n");
        return;
    }

    printf("Gonderilecek miktar: ");
    scanf("%f", &amount);

    if (amount <= 0)
    {
        printf("Gecersiz miktar!\n");
        return;
    }

    if (amount > sender->balance)
    {
        printf("Yetersiz bakiye!\n");
        return;
    }

    sender->balance -= amount;
    accounts[target_index].balance += amount;

    save_accounts();

    printf("Transfer basarili.\n");
    printf("Yeni bakiyeniz: %.2f TL\n", sender->balance);
}

void account_menu(int index)
{
    int choice;

    while (1)
    {
        printf("\n=== HESAP MENUSU ===\n");
        printf("1 - Bakiye Goruntule\n");
        printf("2 - Para Yatir\n");
        printf("3 - Para Cek\n");
        printf("4 - Para Transfer Et\n");
        printf("5 - Cikis Yap\n");
        printf("Secim: ");
        scanf("%d", &choice);

        if (choice == 1)
            show_balance(&accounts[index]);
        else if (choice == 2)
            deposit(&accounts[index]);
        else if (choice == 3)
            withdraw(&accounts[index]);
        else if (choice == 4)
            transfer(&accounts[index]);
        else if (choice == 5)
            break;
        else
            printf("Gecersiz secim!\n");
    }
}

void main_menu(void)
{
    int choice;

    while (1)
    {
        printf("\n=========================\n");
        printf("   TERMINAL BANKA SISTEMI\n");
        printf("=========================\n");
        printf("1 - Hesap Olustur\n");
        printf("2 - Giris Yap\n");
        printf("3 - Cikis\n");
        printf("Secim: ");
        scanf("%d", &choice);

        if (choice == 1)
        {
            create_account();
        }
        else if (choice == 2)
        {
            int index = login();

            if (index != -1)
                account_menu(index);
        }
        else if (choice == 3)
        {
            printf("Program kapatildi.\n");
            break;
        }
        else
        {
            printf("Gecersiz secim!\n");
        }
        system("cls");
    }
}

int main(void)
{
    load_accounts();
    main_menu();
    return 0;
}