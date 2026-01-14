README raw subfolder in ims_data_root folder in nes-lter shared storage
2022-08-23

This subfolder contains data files used by the NES-LTER IMS code library.
"all" is for multi-cruise datasets, such as the Sosik lab's nutrients from Transect cruises.
Cruises (note: OOI cruise legs are separate):
[ar16 Van Mooy cruise prior to start of NES-LTER project]
ar22 JP student cruise Sep 2017
ar24a, ar24b, ar24c OOI Transect fall 2017
ar28a, ar28b OOI Transect spring 2018
ar31a, ar31b, ar31c OOI Transect fall 2018
ar32 JP student cruise Nov 2018
ar34a, ar34b OOI Transect spring 2019
ar38 JP student cruise Sep 2019
ar39a, ar39b OOI Transect fall 2019
ar44 delayed OOI Transect June 2020
ar48a, ar48b OOI Transect fall 2020
ar52a, ar52b OOI Transect spring 2021
ar61a, ar61b OOI Transect fall 2021
at46 LTER Transect winter 2022
en608 LTER Transect winter 2018
en617 LTER Transect summer 2018
en627 LTER Transect winter 2019
en644 LTER Transect summer 2019
en649 LTER Transect winter 2020
en655 LTER Transect summer 2020
en657 RAPID transect fall 2020
en661 LTER Transect winter 2021
en668 LTER Transect summer 2021
en687 LTER Transect summer 2022


Note Manually corrected files

CTD
NO LONGER APPLICABLE - ar24a001.btl - not btl file but manual Niskin entries for discrete water samples
ar24a001.btl & .ros (not served) - manually created by Taylor - created .ros and then ran bottle summary in Seabird software to output btl file
ar24a008.btl - not btl file but manual Niskin entries for discrete water samples
ar24a002.btl-ar24017.btl - added space between Oxsat and Sbeox columns
ar24b009.btl & .asc - combined from 009 and 009b for full btl file and cast
ar28b001.btl & .ros - Taylor still needs to manually make
ar28b001.btl - not btl file but manual Niskin entries for discrete water samples
ar34a020.btl & .asc - combined from 020 and 020b for full btl file and cast
ar38008.btl - added N16 and copied form N15
ar39a006.btl - did not edit but OOI logsheet says skipped N5 and sampled N6-9 but N8 DNE in btl and N5-8 correspond to expected depths for N6-9 so adjust N sampled in Sosik Excel data sheets
ar39a013.btl - not btl file but manual Niskin 7 entry for discrete water samples. Couldn't figure out why N7 btl data DNE.
ar61a*.hdr (*=003, 004, 005) 2024-07-29 Taylor - Add 4 lines: NMEA lat/lon/UTC(Time) and "Store Lat/Lon Data". Got lat/lon from elog and confirmed LTER corrected underway GPS also matches. Used System upload time as NMEAtime. Wasn't sure what to put for store/lat/lon and wasn't sure if it was necessary but just copied to match cast 2 with Append to Every Scan. 
ar61a005.btl - got from .hdr file. See issue above. 
en706_015.btl & .asc - Taylor redid bottle file to include 1-24 whereas it was only 1-12. Depth binned, skipped first 3,000 scans (soak and come to surface) and do NOT throw out scans marked as bad. Pumps turned of during upcast starting at 38m so all oxygen/salt data are bad/suspect shallower during upcast.
en627_003.btl - combine 003.btl & 004.btl for complete 003.btl file

UNDERWAY
ar70b1120_00.csv - combined _00 & _1931, filled in missing data row of 14:51-19:30 - GPS from AR_GPS10_221120_0000.csv, temp/salt/fluor/flow from AR_SSW20_221120_0000.csv
2 more times..... 
ar77 not sure what file but manually edited GPS
hrs2303 - Joanne K wrote special code to consolidate all of ship's underway files because very non-standard output

