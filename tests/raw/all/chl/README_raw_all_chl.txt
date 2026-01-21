README for ims_data_root subfolder raw > all > chl
This folder contains chlorophyll data "raw" to the IMS provided by Sosik lab for "all" cruises.
Versions of these data are curated at the Environmental Data Initiative https://portal.edirepository.org/nis/mapbrowse?packageid=knb-lter-nes.8.1

2023-03-31 Taylor copy updated NESLTERchl butmake backup of current working copy that was compiled to EDI with filename addition 20230331_. Some new Pioneer cruises added since last copy.

2023-03-27 Taylor updated NESLTERchl.xlsx. Made a few edits to indiviudal Niskins as well as all AR31A niskins. Prep for EDI publishing.

2023-03-23 Taylor updated copy. Renamed current working version with "20230323_" at front of filename. 
New Pioneer data for AR44 & AR52A/B which will not be published in this EDI ver2. Still need to give to OOI
Manually edited AR24B C9 btl in vortex to have missing data from ar24b009b.btl

2023-03-08 Taylor updated copy. Filled in a couple missing flags and AR38 now complete. Taylor confirmed API still works.

2023-02-23 Taylor updated copy. Ran many <10s to fully complete several cruises. 

2022-12-21 Updated with new file from sosiknas; significantly more data from Diana running chl.

2021-07-15
Note there are only 2 c's and 1 d replicate. In general, just reps a,b.
Note there is only 1 bucket sample (Niskin 0), and there are comments for this sample from AR24B 20171030 that may explain why 2 a's.

2021-07-15 Curated version of these data available at EDI https://doi.org/10.6073/pasta/798bda0e9ddfeba20f2266e64cf4dd40

2021-04-19 Note cruise AR24B incorrectly had station "L17". It is cast 17 but nearest station L12.

2021-04-09 Stace applied the following fix ONLY TO THE RDS (NOT asking Taylor to do this in Sosiknas):
For EN627 cast 3 niskin 7, we need to 'trick' the API because the btl file for that cast got split.
The cast 3 btl file stops at niskin 6. For the cast 4 (there was no cast 4) btl file, they tripped 6 niskins to get to index 7,
thus the "cast 4" btl file starting with niskin 7 is really for cast 3. For 8 rows: I replaced cast 3 with 4.
Note there ARE corrected bottle summary and bottles files in the "corrected" path on RDS, but this apparently is NOT used for chl API workflow.

2021-04-06 Stace applied the following fix only to the file in RDS (alert Taylor to Sosiknas):
for AR24C Cast 2 changed 2nd row with niskin 3 to 4, changed what was niskin 4 to 5, and changed what was niskin 5 to 6.
For confidence in this fix: Stace and Kate started with the bottle summary file for depth of niskins,
compared depth of niskins to revised OOI log sheet, and
confirmed that the paired chl values were consistent as replicates at same depth.
This now matches the OOI filter ID to the niskin on the revised OOI log sheet.

2021-04-06 "NESLTERchl.xlsx" version uploaded into RDS on 2021-04-06
Stace applied the fix that was previously applied only in RDS (2021-03-10, RDS but not in Sosiknas)
for blank Niskin value EN617 cast 12 niskin 10 filter 5 rep b TAR64.

2021-04-01 Taylor fixed the Niskin values for 2 Niskins that were updated in the OOI sampling metadata (but not yet in OOI data)
for AR24C Cast 2 & 3 Niskin 9 changed to Niskin 8.


