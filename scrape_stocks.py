#%%
from random import choices
import requests
import time
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import pickle
from webdriver_manager.chrome import ChromeDriverManager
    
#%%
from selenium import webdriver
  
# Import Select class
from selenium.webdriver.support.ui import Select

options = webdriver.ChromeOptions() 
options.add_argument("start-maximized")
#options.add_argument("--headless")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

options.add_argument("window-size=1280,800")
#options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
options.add_argument("user-data-dir=C:/Users/user/AppData/Local/Google/Chrome/User Data")
#§options.add_argument('proxy-server=106.122.8.54:3128')
# Using chrome driver
# options = webdriver.firefox.options.Options()
# driver = webdriver.Firefox()

scrap_choice = 'scrap_data'
scrap_mode = {'refresh_urls': 1, 'scrap_data':2}


#%%
#GET STOCK URLS
if scrap_mode[scrap_choice] == scrap_mode['refresh_urls']:
    #not needed just load from txt

    #Init Chrome driver
    driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)

    #Web page url
    url = "https://tr.investing.com/equities/turkey"
    driver.get(url)
#%%

if scrap_mode[scrap_choice] == scrap_mode['refresh_urls']:
    time.sleep(2)
    # Find id of option
    x = driver.find_element_by_id('stocksFilter')
    drop = Select(x)

    # Select by value
    drop.select_by_visible_text('BİST Ulusal Tüm')

    time.sleep(2)
    #sort by names
    stockTable = driver.find_element_by_id('cross_rate_markets_stocks_1')
    nameSort = stockTable.find_element_by_xpath("//table/thead/tr/th[2]")
    nameSort.click()
    stockTableHtml = driver.find_element_by_id('cross_rate_markets_stocks_1').get_attribute('innerHTML')

    stockURLs = []
    stockNames = []
    allStockSoup = BeautifulSoup(stockTableHtml, "html.parser")
    stockInfos = allStockSoup.findAll("td", {"class":"bold left noWrap elp plusIconTd"})
    total = 0
    for href in stockInfos:
        urlRefs = href.findAll('a', href=True)
        stockURLs.append(urlRefs[0]['href'])
        urlNames = href.findAll('a', href=True)
        stockNames.append(urlRefs[0].getText())
        total = total + 1
    print("Total stocks ", total)
        
    with open("stockUrls_15_11_22.txt", "wb") as fp:
        pickle.dump(stockURLs, fp)

    
#%%
#Run this cell to scrap data from the stock urls
elif scrap_mode[scrap_choice] == scrap_mode['scrap_data']:
    with open("stockUrls_15_11_22.txt", "rb") as fp:
        stockURLs = pickle.load(fp)

    url = 'https://tr.investing.com'

    header={'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36'}

    driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)


    stockReturns = [("isim", "fk", "ozGetiri", "aktifGetiri")]

    validStockNames = []
    for i in range(len(stockURLs)):
        stockUrl = url + stockURLs[i] + '-ratios'
        
        driver.get(stockUrl)
        response = driver.page_source
        soup = BeautifulSoup(response, "html.parser")
        
        #response=requests.get(stockUrl,headers=header)

        #soup = BeautifulSoup(response.text, "html.parser")

        table = soup.findAll('table', {"class":"genTbl reportTbl"})
        if len(table) > 3:
            stockName = soup.findAll('h1', {"class":"float_lang_base_1 relativeAttr"})[0].getText()
            priceTable = table[0].findAll("tr", {"class":"child"})
            fk = priceTable[0].findAll("td")[1].getText()
            if fk != '-':
                fk = fk.replace(',', '.')
                #check the second comma if there are more than one comma, invalid number
                dotIndex = fk.find('.')
                if fk.find('.', dotIndex + 1) == -1:
                    fk = float(fk)
                else:
                    fk = None
            else:
                fk = None
            
            
            returnTable = table[3].findAll("tr", {"class":"child startGroup"})
            ozGetiri = returnTable[0].findAll("td")[1].getText()
            if ozGetiri != '-':
                ozGetiri = ozGetiri[:-1]
                ozGetiri = ozGetiri.replace(',', '.')
                #check the second comma if there are more than one comma, invalid number
                dotIndex = ozGetiri.find('.')
                if ozGetiri.find('.', dotIndex + 1) == -1:
                    ozGetiri = float(ozGetiri)
                else:
                    ozGetiri = None
            else:
                ozGetiri = None
            
            aktifGetiri = returnTable[1].findAll("td")[1].getText()
            if aktifGetiri != '-':

                aktifGetiri = aktifGetiri[:-1]
                aktifGetiri = aktifGetiri.replace(',', '.')
                #check the second comma. if there are more than one comma, invalid number
                dotIndex = aktifGetiri.find('.')
                if aktifGetiri.find('.', dotIndex + 1) == -1:
                    aktifGetiri = float(aktifGetiri)
                else:
                    aktifGetiri = None
            else:
                aktifGetiri = None
            
            stockReturns.append((stockName, fk, ozGetiri, aktifGetiri))
            print(f"Done {i} / {len(stockURLs)}")
        else:
            print("Error " + str(i))
        
#%%
if scrap_mode[scrap_choice] == scrap_mode['scrap_data']:

    df = pd.DataFrame(stockReturns[1:],columns=stockReturns[0])
    df.to_csv(r'stockData_15_11_2022.csv', index=False)

    # Sort stocks by the magic formula
    df_read = pd.read_csv(r'stockData_15_11_2022.csv')
    naRemoved = df_read.dropna(axis=0, how='any')
    naRemoved.reset_index(inplace=True)
    naRemoved.pop("index")

    #Sort stock by fk and roa
    sortedFk = naRemoved.sort_values(by=['fk'], axis=0, inplace=False)
    fkIndex = sortedFk.index.values

    sortedRoa = naRemoved.sort_values(by=['aktifGetiri'],axis=0, inplace=False, ascending=False)
    roaIndex = sortedRoa.index.values

    #calculate scores
    stockScore = []
    for row in naRemoved.iterrows():
        fkScore = np.where(fkIndex == row[0])[0][0]
        roaScore = np.where(roaIndex == row[0])[0][0]
        #sum, fk, roa
        stockScore.append([fkScore + roaScore, row[1][1], row[1][3]])

    #sort scores
    stockScores = np.array(stockScore)
    stockScoreIdx = stockScores[:,0].argsort()
    bestFkRoa = stockScores[:,1:][stockScoreIdx]
    bestStocks = naRemoved['isim'][stockScoreIdx].to_frame()
    bestStocks['fk'] = bestFkRoa[:,0]
    bestStocks['roa'] = bestFkRoa[:,1]
    bestStocks.reset_index(inplace=True)
    # bestStocks.to_csv(r'C:\Users\user\Desktop\web_scraping\bestStocks.csv')
    bestStocks.to_excel(r'magicFormulaStocks_15_11_2022.xlsx')

# %%
