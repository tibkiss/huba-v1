import logging

log = logging.getLogger(__name__)

HUBA_DB_URI = 'postgresql://yyyy:XXXX@192.168.212.31/huba'
HUBA_TEST_DB_URI = 'postgresql://yyyy:XXXX@192.168.212.31/huba_test'

from strategy.statarb_params import StatArbParams
import itertools
from copy import deepcopy


StatArbConfig = dict()
# In order to match the paper trading size with the real trading size we need to consider
# the number of traded pairs in both account. The leverage of the accounts should be the
# same to have the similar interests on the borrowed shares.
# The freely available positions at IB is 100 (50 pairs), with quote booster this can be increase.
# The number of pairs traded in a real trading account is around 15.
# Assuming $100k as trading capital then each trade should hold $6.66k 
# Therefore the equity in paper trading should be set to $666k (assuming 100 pairs w/ quote booster)
StatArbConfig['Paper'] = {'AccountCode':    'DU123456',
                          'TWSConnection':  'tws-paper:7500:53', # Host:Port:ConnectionId
                          'Leverage':   1.7,
                          'Pairs': ("DHR_WAT",   "MVF_BHK",   "PNR_DOX",   "LH_STE",    "RS_WCC",    "SLF_AMWD",  "ADBE_EFII",
                                    "INSY_NBIX", "GII_BLV",   "BTI_PM",    "RWR_PUK",   "STFC_AXS",  "FFIC_FISI", "EGBN_JPM",
                                    "BID_FOSL",  "TRTN_CGI",  "SSL_APD",   "APU_SPH",   "MAA_TITN",  "KOF_FMX",   "SASR_INDB",
                                    "YORW_SJW",  "KIRK_SPLS", "AVY_LYTS",  "FHN_COBZ",  "HAFC_AEGN", "EZA_EWH",   "ACC_BIP",
                                    "CXO_TCP",   "ILG_FLY",   "ACM_CRAI",  "PFS_BANC",  "WFC_MSFG",  "DUG_PXH",
                                    "HTGC_GAIN", "EBF_EQR",   "DCI_DORM",  "GILD_DVA",  "ARCC_BKCC", "WFM_SBUX",  "EOG_CLR",
                                    "DGAS_NJR",  "AVB_ESS",   "ADC_RGC",   "EXPO_PZZA", "ELS_FAST",  "HOMB_OZRK", "CERN_CRM",
                                    "HCP_LTC",
                                    )
                          }

StatArbConfig['Real'] = {'AccountCode':    'U123456',
                         'TWSConnection':  'tws-real:7500:53',  # Host:Port:ConnectionId
                         'Leverage':       0.5,
                         'Pairs': ("EZA_EWH",   "WTS_CVCO",  "CXO_TCP",   "ADBE_EFII",  "CRH_MLM",    "MTW_TEX",
                                   "BTI_PM",    "KOF_FMX",   "INSY_NBIX",  "EGBN_JPM"
                                   )
                         }

StatArbConfig['Test'] = {'AccountCode':    'DU476221',
                         'TWSConnection':  '192.168.212.21:7500:77',
                         'Leverage':       1.0,
                         'Pairs':          ()
                         }


# Configuration for the pairs. Use the optimizer to choose the best parameters for the given pair
StatArbPairsParamsShared = {
    ### Nasdaq screening 2013. 05. 01.
    ###################################

    # 2016-07-31 14:04,v1.2-35-g789b1ec,ADSK_JNPR,2014-01-01,2016-12-31,1M,250695,649,0.62,14.27,41.01,15.64,319,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True)"
    ('ADSK', 'JNPR'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=True),  # Unassigned

    # 2016-07-31 14:56,v1.2-35-g789b1ec,ACC_WPC,2014-01-01,2016-12-31,1M,221230,649,0.63,14.26,40.96,13.98,225,"StatArbParams(lookbackWindow=40, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('ACC',  'WPC'):  StatArbParams(lookbackWindow=40, entryZScore=0.5, logPrices=True),  # Unassigned

    ### 2013. 05. 09
    #################
    # 2016-07-30 17:00,v1.2-10-gf0fb4f7,AZPN_MXIM,2014-01-01,2016-12-31,1M,240784,649,0.51,15.35,44.44,20.37,172,"StatArbParams(lookbackWindow=40, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('AZPN', 'MXIM'): StatArbParams(lookbackWindow=40, entryZScore=1.5, logPrices=False),  # Paper

    # 2016-07-30 16:23,v1.2-10-gf0fb4f7,DHR_WAT,2014-01-01,2016-12-31,1M,244016,649,0.37,10.51,29.35,12.12,273,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('DHR',  'WAT'):  StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=True),  # Paper

    # 2016-07-31 14:07,v1.2-35-g789b1ec,MVF_BHK,2014-01-01,2016-12-31,1M,76522,649,0.47,9.23,25.52,3.94,210,"StatArbParams(lookbackWindow=40, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hur)"
    ('MVF',  'BHK'):  StatArbParams(lookbackWindow=40, entryZScore=1.5, logPrices=True),  # Paper

    ### 2013. 09. 16.
    #################

    # Unassigned
    ('GOOG', 'APH'):  StatArbParams(lookbackWindow=40, entryZScore=1.5),  # Unassigned

    # 2016-07-31 15:44,v1.2-35-g789b1ec,MSM_MGRC,2014-01-01,2016-12-31,1M,198557,649,0.03,5.71,15.39,13.68,280,"StatArbParams(lookbackWindow=120, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('MSM',  'MGRC'): StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-07-31 15:45,v1.2-35-g789b1ec,MTW_TEX,2014-01-01,2016-12-31,1M,245629,649,1.04,59.89,234.91,40.56,99,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('MTW',  'TEX'):  StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=False),

    ('KDN',  'CAS'):  StatArbParams(lookbackWindow=75, entryZScore=1.0),  # Unassigned

    # 2016-07-31 14:53,v1.2-35-g789b1ec,MYD_BNA,2014-01-01,2016-12-31,1M,58511,672,-0.33,3.61,9.91,5.91,235,"StatArbParams(lookbackWindow=120, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hu)"
    ('MYD',  'BNA'):  StatArbParams(lookbackWindow=120, entryZScore=0.5, logPrices=False),  # Unassigned

    # 2016-07-31 15:19,v1.2-35-g789b1ec,ADSK_RSTI,2014-01-01,2016-12-31,1M,248439,649,0.65,20.09,60.23,16.51,118,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fals)"
    ('ADSK', 'RSTI'): StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False),  # Unassigned

    ('ISBC', 'SCBT'): StatArbParams(lookbackWindow=45, entryZScore=1.0),  # Unassigned

    # XXX: All backtest results are positive!
    # 2016-07-31 13:59,v1.2-35-g789b1ec,DEL_CVCO,2014-01-01,2016-12-31,1M,53711,649,1.03,30.25,97.52,21.89,237,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('DEL',  'CVCO'): StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, 0.05)),  # Unassigned

    # 2016-07-31 14:38,v1.2-35-g789b1ec,IBM_GLD,2014-01-01,2016-12-31,1M,251676,649,0.62,14.86,42.89,14.60,175,"StatArbParams(lookbackWindow=40, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('IBM',  'GLD'):  StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=False),  # Paper

    # 2016-07-31 15:22,v1.2-35-g789b1ec,CNX_BHI,2014-01-01,2016-12-31,1M,250798,649,0.58,26.98,85.00,31.61,282,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('CNX',  'BHI'):  StatArbParams(lookbackWindow=20, entryZScore=2.0, logPrices=True),  # Real

    # 2016-07-30 16:12,v1.2-10-gf0fb4f7,MSCC_PRGS,2014-01-01,2016-12-31,1M,197036,649,-1.08,-15.51,-35.20,40.03,709,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Tr)"
    ('MSCC', 'PRGS'): StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2016-07-30 17:44,v1.2-10-gf0fb4f7,PPS_TITN,2014-01-01,2016-12-31,1M,183477,649,-1.24,-11.40,-26.79,28.83,741,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Tru)"
    ('PPS',  'TITN'): StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper

    ('MAA',  'TITN'): StatArbParams(lookbackWindow=60, entryZScore=1.0, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2014-11-10 09:36,PMCS_SPIL,2009-01-01,2013-12-31,1M,1254,0.43,13.37,86.71,29.37,289,60,2.00,0.00,600
    # 2014-11-23 21:18,PMCS_SPIL,2013-11-07,2014-11-07,1M,252,0.17,6.26,6.26,17.08,173,60,2.00,0.00,600
    # 2014-11-23 21:18,PMCS_SPIL,2013-11-07,2014-11-07,1M,252,0.58,14.41,14.41,15.73,118,120,2.00,0.00,600
    ('PMCS', 'SPIL'): StatArbParams(lookbackWindow=120, entryZScore=2.0),  # Real

    # 2016-07-30 15:34,v1.2-10-gf0fb4f7,PNR_DOX,2014-01-01,2016-12-31,1M,237635,649,0.44,11.41,32.07,10.66,93,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('PNR',  'DOX'):  StatArbParams(lookbackWindow=20, entryZScore=1.5, logPrices=False),  # Paper

    # 2016-07-31 03:01,v1.2-10-gf0fb4f7,EZA_EWH,2014-01-01,2016-12-31,1M,209741,649,1.17,22.22,67.64,10.37,99,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('EZA',  'EWH'):  StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False),  # Real

    # 2016-07-31 03:20,v1.2-10-gf0fb4f7,NX_IR,2014-01-01,2016-12-31,1M,242644,649,0.51,13.30,37.94,10.34,211,"StatArbParams(lookbackWindow=120, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('NX',   'IR'):   StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=False, limitPriceIncrements=(0.05, None)),

    # 2016-07-30 17:33,v1.2-10-gf0fb4f7,AMG_CFNL,2014-01-01,2016-12-31,1M,191275,649,-0.21,-0.01,-0.02,26.42,338,"StatArbParams(lookbackWindow=100, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fals)"
    ('AMG',  'CFNL'): StatArbParams(lookbackWindow=100, entryZScore=0.5, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-07-31 15:21,v1.2-35-g789b1ec,IILG_FLY,2014-01-01,2016-12-31,1M,157976,649,0.74,18.84,55.97,16.30,224,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    # IILG got renamed to ILG
    ('ILG', 'FLY'):  StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False),  # Paper

    # 2016-07-31 16:38,v1.2-35-g789b1ec,ALKS_MNTA,2014-01-01,2016-12-31,1M,232498,649,-0.02,1.45,3.78,35.15,561,"StatArbParams(lookbackWindow=120, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fals)"
    ('ALKS', 'MNTA'): StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 16:50,v1.2-10-gf0fb4f7,BRKR_ININ,2014-01-01,2016-12-31,1M,207729,649,0.54,18.31,54.19,25.15,196,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fals)"
    ('BRKR', 'ININ'): StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=False),  # Paper

    # 2016-07-31 02:41,v1.2-10-gf0fb4f7,CEB_GPX,2014-01-01,2016-12-31,1M,130561,649,0.92,23.92,73.74,14.41,152,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('CEB',  'GPX'):  StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 15:29,v1.2-10-gf0fb4f7,HOT_AAWW,2014-01-01,2016-12-31,1M,241940,649,0.83,20.58,61.93,17.62,243,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('HOT',  'AAWW'): StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-07-31 16:01,v1.2-35-g789b1ec,CRH_MLM,2014-01-01,2016-12-31,1M,219985,649,0.60,15.92,46.30,11.18,131,"StatArbParams(lookbackWindow=20, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('CRH',  'MLM'):  StatArbParams(lookbackWindow=20, entryZScore=1.5, logPrices=False),  # Real

    # 2016-07-31 14:17,v1.2-35-g789b1ec,SSL_APD,2014-01-01,2016-12-31,1M,237678,649,0.63,18.12,53.57,27.20,190,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('SSL',  'APD'):  StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=False),  # Paper

    # 2016-07-30 16:32,v1.2-10-gf0fb4f7,LH_STE,2014-01-01,2016-12-31,1M,227667,649,0.36,9.84,27.35,10.47,145,"StatArbParams(lookbackWindow=100, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hu)"
    ('LH',   'STE'):  StatArbParams(lookbackWindow=100, entryZScore=0.5, logPrices=True), # Paper

    # XXX: All backtest results are positive!
    # 2016-07-31 15:43,v1.2-35-g789b1ec,CXO_TCP,2014-01-01,2016-12-31,1M,243806,649,1.28,52.98,198.91,51.66,239,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('CXO',  'TCP'):  StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=False),  # Real

    # 2014-12-10 13:07,v1.1-1-g7e3df2b,TAL_CGI,2013-11-07,2014-11-07,1M,73752,252,2.12,42.30,42.30,7.05,134,20,2.00,0.00,600
    # 2014-12-10 10:46,v1.1-1-g7e3df2b,TAL_CGI,2009-01-01,2013-12-31,1M,325893,1254,0.00,-16.93,-60.28,87.09,1288,20,2.00,0.00,600
    ('TAL',  'CGI'):  StatArbParams(lookbackWindow=20, entryZScore=1.75, limitPriceIncrements=(None, 0.05)),  # Obsolete: TAL merges with Triton as TRTN

    # 2016-07-31 16:37,v1.2-35-g789b1ec,TRTN_CGI,2014-01-01,2016-12-31,1M,174974,649,0.74,24.61,76.23,21.97,216,"StatArbParams(lookbackWindow=100, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('TRTN',  'CGI'):  StatArbParams(lookbackWindow=100, entryZScore=0.5, logPrices=False, limitPriceIncrements=(None, 0.05)),  # Paper


    ### Yahoo+ETFDB Backtest 20131120
    ##################################

    # 2016-07-30 15:40,v1.2-10-gf0fb4f7,CSCO_PKE,2014-01-01,2016-12-31,1M,245408,649,0.98,22.21,67.61,12.92,56,"StatArbParams(lookbackWindow=60, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('CSCO', 'PKE'):  StatArbParams(lookbackWindow=60, entryZScore=1.0, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2016-07-31 17:26,v1.2-35-g789b1ec,ACM_CRAI,2014-01-01,2016-12-31,1M,230547,649,1.31,31.50,102.45,10.84,71,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('ACM',  'CRAI'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Unassigned

    # 2016-07-31 17:58,v1.2-35-g789b1ec,UNH_USPH,2014-01-01,2016-12-31,1M,251423,649,1.03,22.71,69.39,10.88,130,"StatArbParams(lookbackWindow=20, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('UNH',  'USPH'): StatArbParams(lookbackWindow=20, entryZScore=1.5, logPrices=False, limitPriceIncrements=(None, 0.05)),  # Unassigned

    # 2014-12-10 13:11,v1.1-1-g7e3df2b,TEVA_MR,2013-11-07,2014-11-07,1M,97426,252,-0.41,-3.58,-3.58,22.06,206,20,1.00,0.00,600
    # 2014-12-10 11:08,v1.1-1-g7e3df2b,TEVA_MR,2009-01-01,2013-12-31,1M,487064,1254,1.07,26.48,221.82,14.75,185,20,1.00,0.00,600
    # Crap in 2014
    ('TEVA', 'MR'):   StatArbParams(lookbackWindow=20, entryZScore=1.0),  # Unassigned


    # XXX: All backtest results are negative! crap.
    # 2016-07-31 17:09,v1.2-35-g789b1ec,DBE_MORN,2014-01-01,2016-12-31,1M,82846,649,-0.20,-4.29,-10.67,37.19,650,"StatArbParams(lookbackWindow=20, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('DBE',  'MORN'): StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=True),  # Unassigned


    # 2016-07-31 17:32,v1.2-35-g789b1ec,ABG_IX,2014-01-01,2016-12-31,1M,176154,649,0.44,15.74,45.72,22.87,168,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hu)"
    ('ABG',  'IX'):   StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=True, limitPriceIncrements=(0.05, None)),  # Paper

    #2016-07-31 18:12,v1.2-35-g789b1ec,ACC_BIP,2014-01-01,2016-12-31,1M,221230,649,0.73,17.25,50.66,16.09,193,"StatArbParams(lookbackWindow=120, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('ACC',  'BIP'):  StatArbParams(lookbackWindow=120, entryZScore=0.5, logPrices=True),  # Real

    # 2016-07-31 16:50,v1.2-35-g789b1ec,VT_EFT,2014-01-01,2016-12-31,1M,160309,649,-0.11,4.91,13.14,5.04,135,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, h)"
    ('VT',   'EFT'):  StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False),  # Paper

    # 2016-07-31 17:06,v1.2-35-g789b1ec,SLX_IIVI,2014-01-01,2016-12-31,1M,148364,649,0.71,18.29,54.11,14.20,190,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('SLX',  'IIVI'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper


    ### Yahoo+ETFDB Backtest 20131120, Lilla selection
    ##################################################
    # 2014-12-10 13:13,v1.1-1-g7e3df2b,NDSN_ROSE,2013-11-07,2014-11-07,1M,92655,252,0.11,5.65,5.65,11.25,77,20,1.00,0.00,600
    # 2014-12-10 11:15,v1.1-1-g7e3df2b,NDSN_ROSE,2009-01-01,2013-12-31,1M,440005,1254,0.45,18.51,132.80,30.99,398,20,1.00,0.00,600
    ('NDSN', 'ROSE'): StatArbParams(lookbackWindow=10, entryZScore=1.0),  # Paper

    # 2016-07-31 02:51,v1.2-10-gf0fb4f7,IHF_USPH,2014-01-01,2016-12-31,1M,67564,649,1.26,20.48,61.57,7.78,267,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('IHF',  'USPH'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    ### Yahoo+ETFDB Backtest 20131120, Tibi selection
    #################################################

    # 2016-07-30 15:56,v1.2-10-gf0fb4f7,HAFC_AEGN,2014-01-01,2016-12-31,1M,141171,649,0.96,24.54,75.96,16.05,389,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('HAFC', 'AEGN'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-31 17:55,v1.2-35-g789b1ec,ATMI_WOOF,2014-01-01,2016-12-31,1M,211894,665,0.70,20.28,62.80,21.45,192,"StatArbParams(lookbackWindow=100, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True)"
    ('ATMI', 'WOOF'): StatArbParams(lookbackWindow=100, entryZScore=2.0, logPrices=True),

    ('EPAY', 'CAM'):  StatArbParams(lookbackWindow=40, entryZScore=1.5, limitPriceIncrements=(0.05, None)),  #
    ('CLR',  'TRAK'): StatArbParams(lookbackWindow=40, entryZScore=1.0),  #
    ('CMC',  'PRE'):  StatArbParams(lookbackWindow=40, entryZScore=1.0),  #

    # 2014-12-10 13:11,v1.1-1-g7e3df2b,ADI_EFR,2013-11-07,2014-11-07,1M,96269,252,1.42,19.75,19.75,8.05,52,80,1.00,0.00,600
    # 2014-12-10 11:08,v1.1-1-g7e3df2b,ADI_EFR,2009-01-01,2013-12-31,1M,484277,1254,0.15,5.20,28.70,49.41,1011,80,1.00,0.00,600
    ('ADI',  'EFR'):  StatArbParams(lookbackWindow=80, entryZScore=1.0),  # Paper

    # 2016-07-30 16:02,v1.2-10-gf0fb4f7,HRC_AIN,2014-01-01,2016-12-31,1M,185461,649,0.80,21.10,63.73,17.99,278,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('HRC',  'AIN'):  StatArbParams(lookbackWindow=10, entryZScore=0.5, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2016-07-31 16:38,v1.2-35-g789b1ec,AJG_WSO,2014-01-01,2016-12-31,1M,229847,649,0.85,27.30,86.20,20.04,230,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('AJG',  'WSO'):  StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=True),  # Paper

    # 2016-07-30 17:10,v1.2-10-gf0fb4f7,ALGN_CVG,2014-01-01,2016-12-31,1M,214992,649,1.59,34.56,114.80,10.08,127,"StatArbParams(lookbackWindow=120, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True)"
    ('ALGN', 'CVG'):  StatArbParams(lookbackWindow=120, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper & Real

    # 2016-07-31 17:59,v1.2-35-g789b1ec,SLF_AMWD,2014-01-01,2016-12-31,1M,197191,649,0.29,12.13,34.31,30.99,262,"StatArbParams(lookbackWindow=40, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('SLF',  'AMWD'): StatArbParams(lookbackWindow=40, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2016-07-31 18:20,v1.2-35-g789b1ec,AMX_CAC,2014-01-01,2016-12-31,1M,246913,649,0.00,4.86,12.99,28.36,208,"StatArbParams(lookbackWindow=100, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('AMX',  'CAC'):  StatArbParams(lookbackWindow=100, entryZScore=1.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 15:42,v1.2-10-gf0fb4f7,BMTC_KEY,2014-01-01,2016-12-31,1M,244513,649,0.94,19.99,59.88,10.46,150,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('BMTC', 'KEY'):  StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, None)),  # Paper

    ### 20141023: Re-scan Yahoo+ETFDB Above Sharpe 0.75
    ###################################################

    # 2016-07-31 17:23,v1.2-35-g789b1ec,BANC_STL,2014-01-01,2016-12-31,1M,179334,649,0.07,6.11,16.49,17.21,475,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('BANC', 'STL'):  StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 16:07,v1.2-10-gf0fb4f7,AN_MYRG,2014-01-01,2016-12-31,1M,227356,649,1.51,34.96,116.42,11.07,75,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('AN',   'MYRG'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False, limitPriceIncrements=(None, 0.05)),  # Paper

    ### 20141102: Re-scan Yahoo+ETFDB Above Sharpe 0.75, fwdtest
    #############################################################

    # 2016-07-30 18:06,v1.2-10-gf0fb4f7,BID_FOSL,2014-01-01,2016-12-31,1M,224910,649,1.45,40.31,139.23,22.57,243,"StatArbParams(lookbackWindow=120, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fal)"
    ('BID', 'FOSL'):  StatArbParams(lookbackWindow=120, entryZScore=1.0, logPrices=False),  # Paper

    # 2016-07-30 15:53,v1.2-10-gf0fb4f7,ADBE_EFII,2014-01-01,2016-12-31,1M,243885,649,1.46,27.25,86.02,6.69,53,"StatArbParams(lookbackWindow=40, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('ADBE','EFII'):  StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=True, limitPriceIncrements=(None, 0.05)),   # Real & Paper

    # 2014-12-10 13:15,v1.1-1-g7e3df2b,APH_EXLP,2013-11-07,2014-11-07,1M,83790,252,0.73,33.39,33.39,15.79,240,20,1.00,0.00,600
    # 2014-12-10 11:24,v1.1-1-g7e3df2b,APH_EXLP,2009-01-01,2013-12-31,1M,462107,1254,0.28,2.88,15.19,67.67,950,20,1.00,0.00,600
    ('APH', 'EXLP'):  StatArbParams(lookbackWindow=20, entryZScore=1.0),   # Paper

    # 2016-07-31 18:24,v1.2-35-g789b1ec,CLNE_MBT,2014-01-01,2016-12-31,1M,235452,649,1.11,44.06,156.03,38.65,202,"StatArbParams(lookbackWindow=100, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fal)"
    ('CLNE','MBT'):   StatArbParams(lookbackWindow=100, entryZScore=1.5, logPrices=False),   # Paper

    # 2016-07-31 18:28,v1.2-35-g789b1ec,BJRI_SMTC,2014-01-01,2016-12-31,1M,189632,649,0.48,14.94,43.12,20.74,144,"StatArbParams(lookbackWindow=40, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('BJRI','SMTC'):  StatArbParams(lookbackWindow=40, entryZScore=1.5, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 16:46,v1.2-10-gf0fb4f7,MAS_SENEA,2014-01-01,2016-12-31,1M,243757,649,-0.02,3.11,8.20,23.40,434,"StatArbParams(lookbackWindow=60, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('MAS', 'SENEA'): StatArbParams(lookbackWindow=60, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2014-12-10 13:18,v1.1-1-g7e3df2b,NIB_COV,2013-11-07,2014-11-07,1M,96844,252,2.20,55.54,55.54,5.85,31,80,1.00,0.00,600
    # 2014-12-10 11:40,v1.1-1-g7e3df2b,NIB_COV,2009-01-01,2013-12-31,1M,484920,1254,0.40,10.60,65.12,25.14,268,20,1.00,0.00,600
    # 2014-12-10 13:17,v1.1-1-g7e3df2b,NIB_COV,2013-11-07,2014-11-07,1M,96844,252,1.33,37.66,37.66,9.18,84,20,1.00,0.00,600
    ('NIB', 'COV'):   StatArbParams(lookbackWindow=20, entryZScore=1.0),  # COV is bought by MDT @ 2015. 01. 27.

    # 2016-07-30 16:46,v1.2-10-gf0fb4f7,RS_WCC,2014-01-01,2016-12-31,1M,210542,649,0.40,11.68,32.91,15.23,297,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, h)"
    ('RS',  'WCC'):   StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2014-12-10 13:19,v1.1-1-g7e3df2b,RWR_PUK,2013-11-07,2014-11-07,1M,60770,252,0.72,11.47,11.47,8.28,82,80,1.00,0.00,600
    # 2014-12-10 11:54,v1.1-1-g7e3df2b,RWR_PUK,2009-01-01,2013-12-31,1M,354695,1254,0.38,10.49,64.24,23.17,546,80,1.00,0.00,600
    ('RWR', 'PUK'):   StatArbParams(lookbackWindow=80, entryZScore=1.0),   # Paper

    # 2014-12-10 13:20,v1.1-1-g7e3df2b,ATW_GES,2013-11-07,2014-11-07,1M,88942,252,2.45,43.93,43.93,8.15,58,20,1.50,0.00,600
    # 2014-12-10 11:59,v1.1-1-g7e3df2b,ATW_GES,2009-01-01,2013-12-31,1M,465053,1254,0.49,-1.90,-9.09,98.59,1301,20,1.50,0.00,600
    ('ATW', 'GES'):   StatArbParams(lookbackWindow=20, entryZScore=1.5),   # Paper

    ### 20141103: Re-scan Yahoo+ETFDB Above Sharpe 0.75, fwdtest + Lilla manual
    ###########################################################################

    # 2016-07-30 16:46,v1.2-10-gf0fb4f7,INSY_NBIX,2014-01-01,2016-12-31,1M,213672,649,0.91,55.35,210.97,54.82,185,"StatArbParams(lookbackWindow=20, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fal)"
    ('INSY', 'NBIX'):  StatArbParams(lookbackWindow=20, entryZScore=1.5, logPrices=False, limitPriceIncrements=(0.05, None)),  # Paper

    # 2014-12-10 13:21,v1.1-1-g7e3df2b,KB_LFC,2013-11-07,2014-11-07,1M,50228,252,1.91,23.66,23.66,3.81,52,60,2.00,0.00,600
    # 2014-12-10 11:57,v1.1-1-g7e3df2b,KB_LFC,2009-01-01,2013-12-31,1M,387062,1254,0.61,15.29,102.96,10.09,161,60,2.00,0.00,600
    ('KB',   'LFC'):   StatArbParams(lookbackWindow=60, entryZScore=2.0),  # Paper

    # 2014-12-10 13:22,v1.1-1-g7e3df2b,CMC_TRAK,2013-11-07,2014-11-07,1M,84860,252,1.79,38.59,38.59,11.23,56,60,2.00,0.00,600
    # 2014-12-10 12:05,v1.1-1-g7e3df2b,CMC_TRAK,2009-01-01,2013-12-31,1M,460186,1254,1.12,29.31,259.28,18.59,162,60,2.00,0.00,600
    ('CMC',  'TRAK'):  StatArbParams(lookbackWindow=60, entryZScore=2.0),  # Paper

    # 2014-12-10 12:11,v1.1-1-g7e3df2b,CRH_RRC,2009-01-01,2013-12-31,1M,483689,1254,0.74,21.88,167.68,19.47,222,40,1.50,0.00,600
    # 2014-12-10 13:23,v1.1-1-g7e3df2b,CRH_RRC,2013-11-07,2014-11-07,1M,95846,252,2.32,42.78,42.78,6.19,30,40,1.50,0.00,600
    ('CRH',  'RRC'):   StatArbParams(lookbackWindow=40, entryZScore=1.5),  # Paper

    ### 20141118: 1M Scan ETFDB
    ######################################################################

    # 2016-07-30 16:43,v1.2-10-gf0fb4f7,TOK_IOO,2014-01-01,2016-12-31,1M,38135,649,0.87,19.64,58.70,2.83,69,"StatArbParams(lookbackWindow=40, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hur)"
    # More TOK Pairs: TOK_IOO, TOK_VT, TOK_GWL, TOK_VTV TOK_DIA, TOK_IVE
    ('TOK',  'IOO'):  StatArbParams(lookbackWindow=40, entryZScore=0.5),  # Paper

    # 2016-07-30 17:03,v1.2-10-gf0fb4f7,GII_BLV,2014-01-01,2016-12-31,1M,74139,649,0.57,12.07,34.12,12.33,416,"StatArbParams(lookbackWindow=20, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('GII',  'BLV'):  StatArbParams(lookbackWindow=20, entryZScore=1.5, logPrices=True),  # Paper

    # 2016-07-30 17:34,v1.2-10-gf0fb4f7,JXI_XRT,2014-01-01,2016-12-31,1M,237265,649,0.33,15.37,44.52,26.04,344,"StatArbParams(lookbackWindow=40, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('JXI',  'XRT'):  StatArbParams(lookbackWindow=40, entryZScore=2.0, logPrices=True),  # Paper

    ### 20141208: 1M Scan Yahoo.US
    ######################################################################

    # 2014-12-04 08:31,v1.0-238-ge66b963,E_GRA,2008-01-01,2013-12-31,1M,516000,1506,0.98,21.82,225.30,17.06,235,60,1.00,0.00,600
    # 2014-12-05 17:05,v1.0-238-ge66b963,FLS_NX,2008-01-01,2013-12-31,1M,548886,1506,1.25,52.92,1165.77,19.78,221,60,1.00,0.00,600
    # 2014-12-06 19:41,v1.0-238-ge66b963,CRS_LDL,2008-01-01,2013-12-31,1M,508574,1506,1.21,39.99,646.60,39.54,359,60,1.00,0.00,600
    # 2014-12-05 18:00,v1.0-238-ge66b963,FLR_MYRG,2008-01-01,2013-12-31,1M,580758,1506,1.49,45.63,845.23,30.16,133,60,1.00,0.00,600

    # Healthcare
    # 2014-12-26 22:02,v1.1-9-g55fca08,LIFE_MR,2008-01-01,2013-12-31,1M,571892,1506,1.30,41.11,683.13,13.48,124,60,1.00,0.00,600
    # 2014-12-26 21:27,v1.1-9-g55fca08,COV_IPCM,2008-01-01,2013-12-31,1M,582438,1506,1.31,35.21,506.54,17.64,428,60,1.00,0.00,600
    # 2014-12-24 02:07,v1.1-9-g55fca08,PKI_USPH,2008-01-01,2013-12-31,1M,550545,1506,1.33,37.70,576.44,37.02,481,60,1.00,0.00,600

    # 2016-07-30 15:28,v1.2-10-gf0fb4f7,LEN_UFPI,2014-01-01,2016-12-31,1M,243542,649,0.80,22.51,68.68,21.16,169,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('LEN',  'UFPI'):  StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2014-12-10 16:16,v1.0-238-ge66b963,BTI_PM,2008-01-01,2013-12-31,1M,562021,1506,1.58,25.66,291.53,10.60,138,60,1.00,0.00,600
    # 2014-12-10 18:59,v1.1-1-g7e3df2b,BTI_PM,2013-11-07,2014-11-07,1M,97702,252,1.00,14.18,14.18,6.94,48,20,1.00,0.00,600
    # 2014-12-10 19:01,v1.1-1-g7e3df2b,BTI_PM,2009-01-01,2013-12-31,1M,487648,1254,1.63,24.98,203.30,11.66,136,20,1.00,0.00,600
    ('BTI',  'PM'):  StatArbParams(lookbackWindow=20, entryZScore=1.0),  # Real

    # 2014-12-15 00:06,v1.0-238-ge66b963,KOF_FMX,2008-01-01,2013-12-31,1M,529040,1506,1.33,29.98,379.12,11.76,238,60,1.00,0.00,600
    # 2014-12-15 07:38,v1.1-2-g621d4ef,KOF_FMX,2013-11-07,2014-11-07,1M,75835,252,1.29,19.62,19.62,5.82,82,20,1.00,0.00,600
    # 2014-12-15 07:32,v1.1-2-g621d4ef,KOF_FMX,2009-01-01,2013-12-31,1M,435646,1254,0.80,17.38,121.99,11.91,442,20,1.00,0.00,600
    ('KOF',  'FMX'):  StatArbParams(lookbackWindow=20, entryZScore=1.0),  # Paper

    # 2016-07-31 02:51,v1.2-10-gf0fb4f7,WTS_CVCO,2014-01-01,2016-12-31,1M,127001,649,1.62,56.59,217.38,25.80,102,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True)"
    ('WTS', 'CVCO'):  StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=True, limitPriceIncrements=(0.05, 0.05)),  # Paper

    # 2016-07-30 17:27,v1.2-10-gf0fb4f7,MDT_USPH,2014-01-01,2016-12-31,1M,245570,649,1.50,28.32,90.06,9.74,112,"StatArbParams(lookbackWindow=60, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('MDT', 'USPH'):  StatArbParams(lookbackWindow=60, entryZScore=2.0, logPrices=False, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2014-12-31 12:00,v1.1-14-g880a0f0,XRAY_MR,2014-01-01,2014-12-31,1M,74981,216,1.54,36.57,30.62,10.05,60,40,1.00,0.00,600
    # 2014-12-31 11:54,v1.1-14-g880a0f0,XRAY_MR,2008-01-01,2013-12-31,1M,554053,1506,1.25,34.79,495.54,23.14,178,40,1.00,0.00,600
    ('XRAY', 'MR'):  StatArbParams(lookbackWindow=40, entryZScore=1.0),  # Real

    # 2015-01-01 21:53,v1.1-19-g01d9262,APU_SPH,2008-01-01,2013-12-31,1M,292153,1506,1.35,25.88,295.64,11.52,109,60,1.00,0.00,600
    # 2015-01-01 23:23,v1.1-21-g276004e,APU_SPH,2008-01-01,2013-12-31,1M,292153,1506,1.87,37.74,577.62,18.64,704,20,1.00,0.00,600
    # 2015-01-01 23:28,v1.1-21-g276004e,APU_SPH,2014-01-01,2014-12-31,1M,64500,251,1.74,22.97,22.87,4.00,67,20,1.00,0.00,600
    ('APU', 'SPH'):  StatArbParams(lookbackWindow=20, entryZScore=1.0, limitPriceIncrements=(None, 0.05)),  # Paper

    # 2015-01-05 07:38,v1.1-26-g00323fd,AWK_MSEX,2014-01-01,2014-12-31,1M,88835,251,1.36,17.25,17.17,3.45,68,20,1.50,0.00,600
    # 2015-01-05 07:34,v1.1-26-g00323fd,AWK_MSEX,2009-01-01,2013-12-31,1M,452484,1254,2.02,32.96,312.68,7.10,143,20,1.50,0.00,600
    ('AWK', 'MSEX'):  StatArbParams(lookbackWindow=20, entryZScore=1.5, limitPriceIncrements=(None, 0.05)),

    # 2016-07-31 03:09,v1.2-10-gf0fb4f7,XEL_ARTNA,2014-01-01,2016-12-31,1M,242949,649,0.98,16.24,47.35,8.13,76,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('XEL', 'ARTNA'): StatArbParams(lookbackWindow=20, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 17:18,v1.2-10-gf0fb4f7,ARTNA_MSEX,2014-01-01,2016-12-31,1M,50219,649,2.13,41.56,144.77,18.12,183,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True)"
    ('ARTNA', 'MSEX'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 18:06,v1.2-10-gf0fb4f7,CHCO_WASH,2014-01-01,2016-12-31,1M,56672,649,1.94,32.10,104.80,15.57,61,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('CHCO',  'WASH'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 17:31,v1.2-10-gf0fb4f7,SYBT_EMCI,2014-01-01,2016-12-31,1M,38310,649,1.05,36.02,120.85,16.99,443,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('SYBT',  'EMCI'): StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 18:34,v1.2-10-gf0fb4f7,WFC_MSFG,2014-01-01,2016-12-31,1M,246241,649,1.57,33.84,111.84,7.64,80,"StatArbParams(lookbackWindow=20, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('WFC',  'MSFG'): StatArbParams(lookbackWindow=20, entryZScore=1.0, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 19:06,v1.2-10-gf0fb4f7,STFC_AXS,2014-01-01,2016-12-31,1M,202643,649,1.60,36.52,122.96,11.66,65,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('STFC',  'AXS'): StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, None)),

    # 2016-07-30 17:42,v1.2-10-gf0fb4f7,SRCE_LKFN,2014-01-01,2016-12-31,1M,56115,649,2.43,47.13,170.32,6.68,64,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('SRCE',  'LKFN'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 17:47,v1.2-10-gf0fb4f7,SFNC_CAC,2014-01-01,2016-12-31,1M,77425,649,1.22,25.74,80.39,11.97,201,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('SFNC',  'CAC'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 19:02,v1.2-10-gf0fb4f7,SASR_INDB,2014-01-01,2016-12-31,1M,79372,649,2.40,46.01,165.07,5.27,109,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('SASR',  'INDB'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 19:20,v1.2-10-gf0fb4f7,RDC_NGS,2014-01-01,2016-12-31,1M,242649,649,2.00,65.76,267.51,16.01,101,"StatArbParams(lookbackWindow=100, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
     ('RDC',  'NGS'): StatArbParams(lookbackWindow=100, entryZScore=1.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 18:27,v1.2-10-gf0fb4f7,PEBO_AJG,2014-01-01,2016-12-31,1M,223513,649,1.40,31.10,100.87,8.88,126,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
     ('PEBO',  'AJG'): StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, None)),

    # 2016-07-30 18:15,v1.2-10-gf0fb4f7,KMT_HAYN,2014-01-01,2016-12-31,1M,214374,649,1.90,72.25,305.71,26.23,63,"StatArbParams(lookbackWindow=100, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
     ('KMT',  'HAYN'): StatArbParams(lookbackWindow=100, entryZScore=0.5, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 18:19,v1.2-10-gf0fb4f7,KIRK_SPLS,2014-01-01,2016-12-31,1M,245204,649,1.32,44.71,159.05,21.71,111,"StatArbParams(lookbackWindow=80, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=Fals)"
    ('KIRK',  'SPLS'): StatArbParams(lookbackWindow=80, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, None)),

    # 2016-07-30 19:32,v1.2-10-gf0fb4f7,IJT_ENY,2014-01-01,2016-12-31,1M,106084,649,0.42,12.74,36.17,12.45,190,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('IJT',  'ENY'): StatArbParams(lookbackWindow=20, entryZScore=2.0, logPrices=False),

    # 2016-07-30 18:42,v1.2-10-gf0fb4f7,FHN_COBZ,2014-01-01,2016-12-31,1M,231603,640,1.14,22.23,66.51,11.85,215,"StatArbParams(lookbackWindow=60, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('FHN',  'COBZ'): StatArbParams(lookbackWindow=60, entryZScore=1.5, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 15:43,v1.2-10-gf0fb4f7,FHCO_ABAX,2014-01-01,2016-12-31,1M,126824,649,0.77,39.16,134.20,94.71,643,"StatArbParams(lookbackWindow=80, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=Tru)"
    ('FHCO',  'ABAX'): StatArbParams(lookbackWindow=80, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 19:28,v1.2-10-gf0fb4f7,FGD_IDV,2014-01-01,2016-12-31,1M,201669,640,-0.28,4.63,12.18,4.97,264,"StatArbParams(lookbackWindow=120, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('FGD',  'IDC'): StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=True),

    # 2016-07-30 18:11,v1.2-10-gf0fb4f7,FFIC_FISI,2014-01-01,2016-12-31,1M,76821,649,2.14,44.40,157.60,8.85,70,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('FFIC',  'FISI'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 18:45,v1.2-10-gf0fb4f7,EGBN_JPM,2014-01-01,2016-12-31,1M,245575,649,1.23,30.09,96.90,13.04,131,"StatArbParams(lookbackWindow=40, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('EGBN',  'JPM'): StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=True, limitPriceIncrements=(0.05, None)),

    # 2016-07-30 17:34,v1.2-10-gf0fb4f7,CLC_ALG,2014-01-01,2016-12-31,1M,162380,649,1.01,20.37,61.21,14.49,185,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,
    ('CLC',  'ALG'): StatArbParams(lookbackWindow=20, entryZScore=2.0, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-07-30 18:18,v1.2-10-gf0fb4f7,BWINB_UVSP,2014-01-01,2016-12-31,1M,44202,649,1.79,36.53,122.97,8.02,90,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('BWINB','UVSP'): StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 18:28,v1.2-10-gf0fb4f7,BRKL_OCFC,2014-01-01,2016-12-31,1M,131247,649,1.11,37.41,126.68,12.52,164,"StatArbParams(lookbackWindow=20, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=Tru)"
    ('BRKL',  'OCFC'): StatArbParams(lookbackWindow=20, entryZScore=0.5, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 18:44,v1.2-10-gf0fb4f7,BHLB_NATL,2014-01-01,2016-12-31,1M,90992,649,1.22,34.33,113.85,11.07,193,"StatArbParams(lookbackWindow=40, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True,)"
    ('BHLB', 'NATL'): StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=True, limitPriceIncrements=(0.05, None)),

    # 2016-07-30 19:11,v1.2-10-gf0fb4f7,BDGE_NBTB,2014-01-01,2016-12-31,1M,87377,649,1.94,33.19,109.21,8.40,87,"StatArbParams(lookbackWindow=10, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('BDGE',  'NBTB'): StatArbParams(lookbackWindow=10, entryZScore=1.5, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-30 18:50,v1.2-10-gf0fb4f7,AVY_LYTS,2014-01-01,2016-12-31,1M,225043,649,1.23,33.13,108.96,12.55,81,"StatArbParams(lookbackWindow=60, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('AVY',  'LYTS'): StatArbParams(lookbackWindow=60, entryZScore=1.5, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-07-31 03:24,v1.2-19-g4610b83,CVCO_GVA,2014-01-01,2016-12-31,1M,143102,649,1.48,44.21,156.71,20.27,94,"StatArbParams(lookbackWindow=40, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False)"
    ('CVCO', 'GVA'): StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-31 04:13,v1.2-22-gdbeb232,YORW_SJW,2014-01-01,2016-12-31,1M,69215,649,1.24,25.59,79.81,10.22,139,"StatArbParams(lookbackWindow=40, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('YORW',  'SJW'): StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-07-31 05:13,v1.2-22-gdbeb232,FIW_REM,2014-01-01,2016-12-31,1M,166828,649,0.22,7.68,20.99,8.53,405,"StatArbParams(lookbackWindow=100, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False,)"
    ('FIW',  'REM'): StatArbParams(lookbackWindow=100, entryZScore=0.5, logPrices=False),

    # 2016-07-31 05:24,v1.2-22-gdbeb232,DUG_PXH,2014-01-01,2016-12-31,1M,103616,649,0.04,3.99,10.59,27.25,766,"StatArbParams(lookbackWindow=10, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, h)"
    ('DUG',  'PXH'): StatArbParams(lookbackWindow=10, entryZScore=1.5, logPrices=True),

    # 2016-07-31 05:58,v1.2-22-gdbeb232,UYG_VV,2014-01-01,2016-12-31,1M,129302,649,0.57,22.03,66.98,15.98,374,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, h)"
    ('UYG',  'VV'): StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False),

    # 2016-10-12 05:58,v1.2-120-g767e46e,AEP_ARTNA,2014-01-01,2016-12-31,1M,243980,700,0.50,1.48,9.73,29.43,6.84,146,191,126,65,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('AEP',  'ARTNA'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05)),

    # 2016-10-12 03:29,v1.2-120-g767e46e,MAR_AAWW,2014-01-01,2016-12-31,1M,243520,700,0.72,1.43,20.50,67.86,23.19,540,380,237,143,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('MAR',  'AAWW'): StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-10-12 06:40,v1.2-120-g767e46e,PFS_BANC,2014-01-01,2016-12-31,1M,135388,700,-0.48,-0.01,-0.66,-1.83,22.77,958,207,113,94,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('PFS',  'BANC'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-10-12 07:14,v1.2-120-g767e46e,HTGC_GAIN,2014-01-01,2016-12-31,1M,165177,700,0.04,0.63,5.14,14.94,21.05,576,128,74,54,"StatArbParams(lookbackWindow=80, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('HTGC',  'GAIN'): StatArbParams(lookbackWindow=80, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, None)),

    # 2016-10-12 07:31,v1.2-120-g767e46e,EBF_EQR,2014-01-01,2016-12-31,1M,239521,700,0.56,1.23,17.02,54.75,24.76,189,123,80,43,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('EBF',  'EQR'): StatArbParams(lookbackWindow=20, entryZScore=2.0, logPrices=True, limitPriceIncrements=(0.05, None)),

    # 2016-10-12 06:21,v1.2-120-g767e46e,DCI_DORM,2014-01-01,2016-12-31,1M,202968,700,0.69,1.66,13.10,40.78,17.16,313,46,33,13,"StatArbParams(lookbackWindow=40, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('DCI',  'DORM'): StatArbParams(lookbackWindow=40, entryZScore=1.0, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-10-12 06:40,v1.2-120-g767e46e,FCBC_CVBF,2014-01-01,2016-12-31,1M,183806,700,1.21,2.37,17.98,58.31,10.62,217,510,299,211,"StatArbParams(lookbackWindow=10, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('FCBC',  'CVBF'): StatArbParams(lookbackWindow=10, entryZScore=1.5, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-10-12 07:19,v1.2-120-g767e46e,GILD_DVA,2014-01-01,2016-12-31,1M,245749,700,0.90,1.85,18.06,58.60,14.11,117,44,33,11,"StatArbParams(lookbackWindow=80, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('GILD',  'DVA'): StatArbParams(lookbackWindow=80, entryZScore=1.5, logPrices=True),

    # 2016-10-12 07:55,v1.2-120-g767e46e,OHI_WPC,2014-01-01,2016-12-31,1M,235694,700,0.15,1.04,6.58,19.36,8.73,121,46,28,18,"StatArbParams(lookbackWindow=120, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('OHI',  'WPC'): StatArbParams(lookbackWindow=120, entryZScore=1.0, logPrices=False),

    # 2016-10-12 06:20,v1.2-120-g767e46e,ARCC_BKCC,2014-01-01,2016-12-31,1M,233427,700,0.43,1.56,10.77,32.86,12.86,88,268,154,114,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('ARCC',  'BKCC'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False),

    # 2016-10-12 06:51,v1.2-120-g767e46e,DGAS_NJR,2014-01-01,2016-12-31,1M,171628,700,0.42,1.71,24.11,82.20,58.11,292,97,64,33,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('DGAS',  'NJR'): StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-10-12 07:18,v1.2-120-g767e46e,GEOS_TRMB,2014-01-01,2016-12-31,1M,230960,700,0.37,0.70,12.72,39.47,24.78,311,28,18,10,"StatArbParams(lookbackWindow=60, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('GEOS',  'TRMB'): StatArbParams(lookbackWindow=60, entryZScore=2.0, logPrices=True, limitPriceIncrements=(0.05, None)),

    # 2016-10-12 07:40,v1.2-120-g767e46e,ES_MSEX,2014-01-01,2016-12-31,1M,240381,700,0.35,1.21,8.77,26.31,16.08,136,83,59,24,"StatArbParams(lookbackWindow=40, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('ES',  'MSEX'): StatArbParams(lookbackWindow=40, entryZScore=1.5, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-10-12 06:20,v1.2-120-g767e46e,CFR_GABC,2014-01-01,2016-12-31,1M,202240,700,-0.29,0.23,1.62,4.56,14.08,288,132,71,61,"StatArbParams(lookbackWindow=10, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('CFR',  'GABC'): StatArbParams(lookbackWindow=10, entryZScore=2.0, logPrices=False, limitPriceIncrements=(None, 0.05)),

    # 2016-10-12 07:02,v1.2-120-g767e46e,DCOM_CBU,2014-01-01,2016-12-31,1M,117905,700,1.08,2.03,21.63,72.26,11.67,297,70,43,27,"StatArbParams(lookbackWindow=120, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('DCOM',  'CBU'): StatArbParams(lookbackWindow=120, entryZScore=1.0, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-10-12 07:05,v1.2-120-g767e46e,AVB_ESS,2014-01-01,2016-12-31,1M,219480,700,0.95,2.48,11.76,36.18,6.63,91,612,367,245,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('AVB',  'ESS'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=True),

    # 2016-10-12 06:44,v1.2-120-g767e46e,NLY_CMO,2014-01-01,2016-12-31,1M,244912,700,-0.27,0.63,3.03,8.66,14.54,349,104,64,40,"StatArbParams(lookbackWindow=120, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('NLY',  'CMO'): StatArbParams(lookbackWindow=120, entryZScore=0.5, logPrices=True),

    # 2016-10-12 07:01,v1.2-120-g767e46e,ADC_RGC,2014-01-01,2016-12-31,1M,219924,700,0.16,0.96,6.76,19.91,12.69,134,30,22,8,"StatArbParams(lookbackWindow=60, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('ADC',  'RGC'): StatArbParams(lookbackWindow=60, entryZScore=1.0, logPrices=True),

    # 2016-10-12 07:24,v1.2-120-g767e46e,HR_UBA,2014-01-01,2016-12-31,1M,205805,700,0.86,2.13,12.33,38.13,9.13,137,294,180,114,"StatArbParams(lookbackWindow=60, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('HR',  'UBA'): StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=False),

    # 2016-10-12 07:44,v1.2-120-g767e46e,EXPO_PZZA,2014-01-01,2016-12-31,1M,172808,700,0.64,1.77,17.86,57.83,19.07,259,66,41,25,"StatArbParams(lookbackWindow=20, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('EXPO',  'PZZA'): StatArbParams(lookbackWindow=20, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, 0.05)),

    # 2016-10-12 06:32,v1.2-120-g767e46e,OEF_EPS,2014-01-01,2016-12-31,1M,194441,700,-0.11,2.85,4.41,12.73,5.47,163,84,44,40,"StatArbParams(lookbackWindow=60, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('OEF',  'EPS'): StatArbParams(lookbackWindow=60, entryZScore=2.0, logPrices=False),

    # 2016-10-12 06:58,v1.2-120-g767e46e,EDE_UTL,2014-01-01,2016-12-31,1M,144677,700,0.09,0.89,5.98,17.50,20.50,384,28,15,13,"StatArbParams(lookbackWindow=80, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('EDE',  'UTL'): StatArbParams(lookbackWindow=80, entryZScore=2.0, logPrices=True, limitPriceIncrements=(0.05, 0.05)),

    # 2016-10-12 07:34,v1.2-120-g767e46e,HCP_LTC,2014-01-01,2016-12-31,1M,244039,700,0.59,1.45,10.93,33.38,13.60,175,362,229,133,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('HCP',  'LTC'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=True),

    # 2016-10-12 06:30,v1.2-120-g767e46e,CTWS_IDA,2014-01-01,2016-12-31,1M,160615,700,0.67,1.61,11.95,36.83,10.99,165,986,578,408,"StatArbParams(lookbackWindow=10, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('CTWS',  'IDA'): StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=False, limitPriceIncrements=(0.05, None)),

    # 2016-10-12 07:05,v1.2-120-g767e46e,WFM_SBUX,2014-01-01,2016-12-31,1M,246120,700,0.27,1.31,11.65,35.81,34.64,328,16,10,6,"StatArbParams(lookbackWindow=40, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('WFM',  'SBUX'): StatArbParams(lookbackWindow=40, entryZScore=2.0, logPrices=False),

    # 2016-10-12 07:28,v1.2-120-g767e46e,EOG_CLR,2014-01-01,2016-12-31,1M,246636,700,0.51,1.44,21.89,73.29,28.06,396,288,173,115,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('EOG',  'CLR'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=False),

    # 2016-10-12 08:11,v1.2-120-g767e46e,BWA_CGNX,2014-01-01,2016-12-31,1M,239060,700,1.05,2.41,23.50,79.73,15.01,135,24,17,7,"StatArbParams(lookbackWindow=120, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('BWA',  'CGNX'): StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=False),

    # 2016-10-12 07:44,v1.2-120-g767e46e,HOMB_OZRK,2014-01-01,2016-12-31,1M,194401,700,0.60,2.74,19.50,64.03,15.91,350,226,137,89,"StatArbParams(lookbackWindow=40, entryZScore=0.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('HOMB',  'OZRK'): StatArbParams(lookbackWindow=40, entryZScore=0.5, logPrices=False),

    # 2016-10-12 08:11,v1.2-120-g767e46e,MD_CNC,2014-01-01,2016-12-31,1M,227755,700,0.46,4.92,10.23,31.05,89.63,278,12,8,4,"StatArbParams(lookbackWindow=100, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('MD',  'CNC'): StatArbParams(lookbackWindow=100, entryZScore=2.0, logPrices=False),

    # 2016-10-12 08:17,v1.2-120-g767e46e,CERN_CRM,2014-01-01,2016-12-31,1M,244559,700,0.82,1.62,17.66,57.11,11.80,242,64,42,22,"StatArbParams(lookbackWindow=40, entryZScore=1.5, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('CERN',  'CRM'): StatArbParams(lookbackWindow=40, entryZScore=1.5, logPrices=False),

    # 2016-10-12 07:06,v1.2-120-g767e46e,ELS_FAST,2014-01-01,2016-12-31,1M,240775,700,0.39,1.03,9.77,29.56,13.63,283,378,258,120,"StatArbParams(lookbackWindow=10, entryZScore=1.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=True, hurstEnabled=False, adfullerEnabled=False)"
    ('ELS',  'FAST'): StatArbParams(lookbackWindow=10, entryZScore=1.0, logPrices=True),

    # 2016-10-12 07:56,v1.2-120-g767e46e,EQY_EGP,2014-01-01,2016-12-31,1M,203627,700,-0.82,0.10,0.32,0.88,11.10,489,14,8,6,"StatArbParams(lookbackWindow=120, entryZScore=2.0, exitZScore=0.0, earningsCeaseFire=False, logPrices=False, hurstEnabled=False, adfullerEnabled=False)"
    ('EQY',  'EGP'): StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=True),

    # No optimization was done!!
    ('AQN',  'UTL'): StatArbParams(lookbackWindow=60, entryZScore=1.5, logPrices=False, limitPriceIncrements=(None, 0.05)),



    # ('',  ''): StatArbParams(lookbackWindow=60, entryZScore=0.5, logPrices=False),
}

# Create two separate lists from the shared to allow account based customization
StatArbPairsParams = { 'Real' : deepcopy(StatArbPairsParamsShared),
                       'Paper': deepcopy(StatArbPairsParamsShared),
                       'Test':  deepcopy(StatArbPairsParamsShared) }

StatArbPairsParams['Paper'][('EZA',  'EWH')] = StatArbParams(lookbackWindow=80, entryZScore=1.5, logPrices=False)
StatArbPairsParams['Paper'][('KOF',  'FMX')] = StatArbParams(lookbackWindow=20, entryZScore=1.5)
StatArbPairsParams['Paper'][('BTI',  'PM')]  = StatArbParams(lookbackWindow=20, entryZScore=1.5)
StatArbPairsParams['Paper'][('ADBE','EFII')] = StatArbParams(lookbackWindow=40, entryZScore=2.0, logPrices=True, limitPriceIncrements=(None, 0.05))
StatArbPairsParams['Paper'][('CXO',  'TCP')] = StatArbParams(lookbackWindow=60, entryZScore=2.0, logPrices=False)
StatArbPairsParams['Paper'][('ACC',  'BIP')] = StatArbParams(lookbackWindow=120, entryZScore=2.0, logPrices=True)
StatArbPairsParams['Paper'][('INSY', 'NBIX')] = StatArbParams(lookbackWindow=20, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, None)) # Lower z-score from 1.5 to 1.0
StatArbPairsParams['Paper'][('KIRK', 'SPLS')] = StatArbParams(lookbackWindow=80, entryZScore=1.0, logPrices=False, limitPriceIncrements=(0.05, None)) # Lower z-score from 1.0 to 0.5
StatArbPairsParams['Paper'][('MTW',  'TEX')] =  StatArbParams(lookbackWindow=10, entryZScore=0.5, logPrices=False) # Change logPrices to False : this works indeed better!


def generateStrategyParms(pairs, leverage=1.0, tag=''):
    """Generates parameters for the optimization"""
    class myIterator:
        def __init__(self, pairs):
            # Fixed parameters
            self._pairs = pairs
            self._live = False
            self._broker = None
            self._leverage = leverage
            self._tag = tag

            # Optimizable parameters
            parameters = {
                'lookbackWindow': [10, 20, 40, 60, 80, 100, 120],
                'entryZScore': [0.5, 1.0, 1.5, 2.0],
                'zScoreUpdateBuffer': [1, 2, 5, 10],
                'logPrices': [True, False]
            }

            # Create all the iterations for the parameters, Tuples are returned (live, broker, olsWin, entryZ, exitZ)
            self._iterations = list(self._product(parameters))
            self._iterationPos = 0

            log.info("Parameters to optimize: %s", parameters)
            log.info("%d possible configurations" % len(self._iterations))

        def _product(self, dicts):
            return (dict(itertools.izip(dicts, x)) for x in itertools.product(*dicts.itervalues()))

        def __iter__(self):
            return self

        def next(self):
            while self._iterationPos < len(self._iterations):
                statArbParams = {}
                for pair in self._pairs:
                    strategy_params = None
                    # Check if the config exists in the statarb config registry
                    for account_type in ['Real', 'Paper', 'Test']:
                        if pair in StatArbPairsParams[account_type]:
                            strategy_params = StatArbPairsParams[account_type][pair]
                            break

                    if strategy_params is None:
                        strategy_params = StatArbParams()

                    # Override config parameters: namedtuple is immutable, need to use
                    # _replace() to modify the parameters
                    strategy_params = strategy_params._replace(**self._iterations[self._iterationPos])

                    statArbParams[pair] = strategy_params
                self._iterationPos += 1

                # Return the input parameters for the BrokerAgent instance
                return self._broker, self._live, statArbParams, self._leverage, self._tag
            else:
                raise StopIteration

    return myIterator(pairs)
