
# %%
import pandas as pd
from datetime import datetime, timedelta
from functions import *
import calendar
import warnings
warnings.filterwarnings("ignore")

date =  datetime.now().strftime('%d-%m-%Y')
base_dir_format = datetime.now().strftime('%d.%m.%y')
base_dir = f's:\\{base_dir_format}'
result_directory = 's:\\playground'
create_folder_if_not_exists(result_directory)
error_count = 0
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 5)
pd.set_option('display.float_format', lambda x: '%.2f' % x)

sub_types = ['beIN Quartar Installment', 'CNE Subscriber', 'MCE staff (CNE staff)',
            'BeIN sports CC', 'beIN Bi Installment', 'Corporate Subscriber', 
            'Bein NC', 'Bulk DTH customer', 'beIN Installment Sub']

# %%
ftpartialname = 'NEWCNEFINTRANSRPT'
newsalespartialname = 'CNENEWCAPTURERPT'
disconnection_partial_name = 'DailyDisconnectionReport.CSV'
beindate_partial_name = 'BEINDATANEWRPT'

ftFoundFiles = search_files(base_dir,ftpartialname)
newsalesFoundFiles=search_files(base_dir,newsalespartialname)
disconnection_found_files = search_files(base_dir, disconnection_partial_name)
beindata_found_files = search_files(base_dir, beindate_partial_name)


print(ftFoundFiles)
print(newsalesFoundFiles)
print(disconnection_found_files)
print(beindata_found_files)


# %%
if len(ftFoundFiles)==0:
        error_count +=1
        raise Exception('[Error] FT File Not Found')
else:
    if checkModificationDate(ftFoundFiles[0]):
        ft = pd.read_csv(ftFoundFiles[0],dtype='str',on_bad_lines='skip')
    else:
        raise Exception('[Error] FT File Wrongly Dated')    


if len(newsalesFoundFiles)==0:
    error_count +=1
    raise Exception('[Error] New Sales Report Not Found')
else:
    if checkModificationDate(newsalesFoundFiles[0]):
        newsales = pd.read_csv(newsalesFoundFiles[0], dtype='str')
        newsales['Customer Created Date'] = pd.to_datetime(newsales['Customer Created Date'], dayfirst=True)
        newsales.to_csv('checkdates.csv', index = False)   
    else:
        raise Exception('[Error] New Sales File Wrongly Dated')
    
    
if len(beindata_found_files)==0:
    error_count +=1
    raise Exception('[Error] Beindata Report Not Found')
else:
    if checkModificationDate(beindata_found_files[0]):
        beindata = pd.read_csv(beindata_found_files[0],dtype="str")
        beindata = beindata.drop(beindata[beindata['Contract Number']=='3532916'].index) #wrong dated contract
    else:
        raise Exception('[Error] Beindata File Wrongly Dated')
    
    
if len(disconnection_found_files)==0:
    error_count +=1
    raise Exception('[Error] Disconnection Report Not Found')
else:
    if checkModificationDate(disconnection_found_files[0]):
        disconnection = pd.read_csv(disconnection_found_files[0],dtype="str", 
                                    usecols=["Customer Number", "Contract Number", "Action Date", "Affected Plan", "Reason For Disconnect/Suspended", "Current Plan Status"])
    else:
        raise Exception('[Error] Disconnection Wrongly Dated')

# %%

# beindata = beindata.loc[~beindata['End Date'].isna()]
# beindata.loc[beindata['End Date'].str.contains('3000')]

# %%
beindata = beindata.loc[beindata['Contract Number']!= '2098194']

commercial_sub_types = ['Clubs','Hotels','Muds','Bein Companies PV']
type_filter = beindata['Customer Type'].isin(commercial_sub_types)
status_filter = beindata['Status']=='Active'
beindata_commercial = beindata.loc[type_filter & status_filter]

beindata = beindata.loc[beindata['Customer Type'].isin(sub_types)]
beindata_active_suspended = beindata.loc[beindata['Status'].isin(['Active','Suspended'])]

beindata['End Date'] = pd.to_datetime(beindata['End Date'], dayfirst=True)

disconnection['Action Date'] = pd.to_datetime(disconnection['Action Date'],dayfirst=True)
disconnection['Action Date'] = disconnection['Action Date'].dt.date
disconnection = disconnection.loc[(disconnection['Current Plan Status']=='Expired')]
disconnection = disconnection.loc[~(disconnection['Customer Number'].isin(beindata_active_suspended['Customer Number']))]
disconnection = disconnection.loc[~(disconnection['Affected Plan'].str.lower().str.contains('art'))]


disconnection.to_csv(f'{result_directory}/disconnected.csv',index=False)

# %%
ft['Created Date'] = pd.to_datetime(ft['Created Date'],dayfirst=True)

ft['Amount'] = pd.to_numeric(ft['Amount'])
ft.loc[ft['Jv Type'] == 'Debit',['Amount']] = ft['Amount'] * -1
ft = ft.loc[ft['Smartcard']!='33333333333']

period_startdays = 1
period_enddays = 1


tempstart = '2025-01-01'
tempend = '2025-12-31'

if datetime.now().weekday()==6: #if sunday work on days from thursday to sunday
    period_startdays=3

dstart= ((datetime.now()-timedelta(days=period_startdays)).replace(hour=0, minute=0, second=0, microsecond=0))
dend = ((datetime.now()-timedelta(days=period_enddays)).replace(hour=0, minute=0, second=0, microsecond=0))

ftnew = ft.loc[(ft['Created Date']>=tempstart) & (ft['Created Date']<=tempend)]

ftnew = ftnew.loc[ftnew['Doc Type'].isin(['JV', 'Payment'])]
ftnew = ftnew.loc[ftnew['Channel Provider'].isin(['beIN'])]
ftnew = ftnew.loc[ftnew['Doc Status'].isin(['Posted'])]


# %%
ftnew['month'] = ftnew['Created Date'].dt.month
ftnew['year'] = ftnew['Created Date'].dt.year
ftnew['weekday'] = ftnew['Created Date'].dt.weekday.apply(lambda x: calendar.day_name[x])
ftnew['Default Entity Type'] = ftnew['Default Entity Type'].str.replace('Partner','beIN')
ftnew['Default Entity Type'] = ftnew['Default Entity Type'].str.replace('Bein','beIN')


online_users = [ 'Mobile_App', 'FAWRY', 'EFINANCE','CNE_WebSite',  'SAHL', 'Cashcall','Opay','FAWRYLINK']

ftnew['isOnline']=0
ftnew.loc[ftnew['User Name'].isin(online_users),'isOnline']=1
ftnew['User Entity'] = ftnew['User Fullname'].apply(lambda x: ' '.join(x.split()[:-1]))
ftnew['isCne'] = 'beIN'
ftnew.loc[ftnew['Default Entity Type'].str.lower().str.contains('cne'),'isCne']='CNE'


ftnew.loc[ftnew['Default Entity Type']=='CNE Head Office','User Entity'] = 'CNE Head Office'
ftnew.loc[ftnew['Default Entity Type']=='Partner Head Office','User Entity'] = 'Partner Head Office'
ftnew.loc[ftnew['User Entity'].str.contains('Omrania'),'User Entity'] = 'EDD Omrania'
replace_values = ['Agent','agent','user', 'User','Sharaf','DG']
ftnew['User Entity'] = ftnew['User Entity'].replace(replace_values,'', regex=True).str.strip()


ftnew['isDTH'] = 'DTH'
commercial_entities = ['beIN Commercial Warehouse','CNE Commercial Warehouse','CNE Commercial Sales Team']
ftnew.loc[ftnew['Subscriber Entity'].isin(commercial_entities),'isDTH'] = 'Commercial'
ftnew.loc[ftnew['Subscriber Entity']=='beIN Commercial Warehouse','isCne']='beIN'

ftnew['isShowroom'] = False
showrooms_entities = ['Mohandeseen Showroom','Maadi showroom']
ftnew.loc[ftnew['Collecting Entity'].isin(showrooms_entities),'isShowroom'] = True

print (ftnew.shape[0])

ftnew.to_csv(f'{result_directory}/ftnew.csv',index=False)

# %%

#newsales['Customer Created Date'] = pd.to_datetime(newsales['Customer Created Date'],dayfirst=False)
newsales = newsales.loc[~newsales['Box Number'].isna()]
newsales = newsales.loc[~newsales['Plan'].isna()]


newsales['isCne']='beIN'

ftnew_commercial_bein = ftnew.loc[(ftnew['isDTH']=='Commercial') & (ftnew['isCne']=='beIN')]


newsales['Payment Amount'] = pd.to_numeric(newsales['Payment Amount'])
newsales = newsales.loc[(newsales[ 'Customer Status'] == 'Active')]
newsales = newsales.loc[(newsales['Channel Provider']=='beIN')]


newsales['User Entity'] = newsales['User Name'].apply(lambda x: ' '.join(x.split()[:-1]))

# newsales['isDTH'] = 'DTH'
# newsales.loc[newsales['Plan'].str.lower().str.startswith('com'),'isDTH'] = "Commercial"


# link with ftnew to get the subscriber entity

mini_ftnew = ftnew.loc[:,['Subscriber Nr','isDTH']]
mini_ftnew = mini_ftnew.drop_duplicates()

newsales = pd.merge(left=newsales,right=mini_ftnew , left_on="Customer Number", right_on="Subscriber Nr")
newsales = newsales.drop("Subscriber Nr", axis=1)

newsales.loc[newsales['Dealer Type'].str.lower().str.contains('cne'),'isCne']='CNE'
newsales.loc[newsales['Dealer Type']=='CNE Head Office','User Entity'] = 'CNE Head Office'
newsales.loc[newsales['Dealer Type']=='Partner Head Office','User Entity'] = 'Partner Head Office'
newsales.loc[newsales['User Entity'].str.contains('Omrania'),'User Entity'] = 'EDD Omrania'
replace_values = ['Agent','agent','user', 'User','Sharaf','DG']
newsales['User Entity'] = newsales['User Entity'].replace(replace_values,'', regex=True).str.strip()

newsales.loc[newsales['Customer Number'].isin(ftnew_commercial_bein['Subscriber Nr']),'isCne'] = 'beIN'



newsales.to_csv(f'{result_directory}/newcapture.csv',index=False)

pd.DataFrame( {'date':newsales['Customer Created Date'].unique()}).to_csv('dates.csv',index=False)


# %%
commercial = pd.read_excel(f'{result_directory}/cafe.xlsx', parse_dates=['Date'])
commercial['source'] = 'CNE'
commercial.loc[commercial['via'].str.lower()=='bein','source'] = 'beIN'
commercial.loc[~(commercial['via'].str.lower()=='bein') & ~(commercial['via'].str.lower()=='cne'),'source'] = 'CNE Dealers'
commercial.to_csv(f'{result_directory}/commercial.csv',index=False)


# %% CURRENT COMMERCIAL COUNT

commercial_count = len(beindata_commercial['Customer Number'].unique())
active_commercial = pd.read_csv(f'{result_directory}/commercial_active.csv', parse_dates=['date'], dayfirst=True)
date_id = datetime.now().strftime('%Y-%m-%d')
#active_commercial['date'] = pd.to_datetime(active_commercial['date'],dayfirst=True)
active_commercial = insert_or_update(active_commercial,date_id,commercial_count)
active_commercial.to_csv(f'{result_directory}/commercial_active.csv',index=False)


# %% CURRENT SUBSCRIBER COUNT
beindata_active = beindata.loc[beindata['Status']=='Active']
activecount = len(pd.unique(beindata_active['Decoder']))
active = pd.read_csv(f'{result_directory}/active.csv', parse_dates=['date'], dayfirst=True)
date_id = datetime.now().strftime('%d/%m/%Y')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
to_disconnect = beindata.loc[beindata['End Date'] == yesterday]
to_disconnect_count = len (pd.unique(to_disconnect['Customer Number']))
active = insert_or_update(active,yesterday,activecount-to_disconnect_count)
active.to_csv(f'{result_directory}/active.csv',index=False)


beindata.loc[beindata['End Date'] == yesterday].to_csv("to disconnet.csv",index=False)


# %%
disconnection['Action Date'] = pd.to_datetime(disconnection['Action Date'],dayfirst=True)


# %%
disconnection['year'] = disconnection['Action Date'].dt.year
disconnection['month'] = disconnection['Action Date'].dt.month

disconnection =  disconnection.drop_duplicates()


# %%
disconnection = disconnection.loc[(disconnection['year']==2025) & (disconnection['month']==1)]

# %%
disconnection.loc[~disconnection['Customer Number'].isin(beindata['Customer Number'])]

# %%



