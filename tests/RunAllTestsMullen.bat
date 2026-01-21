rem Runs all NESLTER API 2 Selenium Webdriver automated tests in Windows cmd prompt launching Chrome. Takes about 5 minutes to run. Not for run in docker container.
rem create /data/token.txt for nes-lter-api.whoi.edu
cmd /c node station.js public > API2TestingonMullen.log 
cmd /c node vessels.js public >> API2TestingonMullen.log 
cmd /c node cruise.js public >> API2TestingonMullen.log 
cmd /c node cast.js public >> API2TestingonMullen.log 
cmd /c node niskin.js public >> API2TestingonMullen.log 
cmd /c node bottle.js public >> API2TestingonMullen.log 
cmd /c node metadata.js public >> API2TestingonMullen.log 
cmd /c node event.js public >> API2TestingonMullen.log 
cmd /c node underway.js public >> API2TestingonMullen.log 
cmd /c node hplc.js public >> API2TestingonMullen.log 
cmd /c node nut.js public >> API2TestingonMullen.log 
cmd /c node chl.js public >> API2TestingonMullen.log 
cmd /c node cruise_track.js headful public >> API2TestingonMullen.log
cmd /c node landing.js headful public >> API2TestingonMullen.log


rem cmd /c node upload.js headful public >> API2TestingonMullen.log 









