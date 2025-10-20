rem Runs all NESLTER API 2 Selenium Webdriver automated tests in Windows cmd prompt launching Chrome. Takes about 5 minutes to run. 
rem create /data/token.txt for localhost admin user token
cmd /c node station.js > API2Testing.log 
>> API2Testing.log echo.
cmd /c node vessels.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node cruise.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node cast.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node niskin.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node bottle.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node metadata.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node event.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node underway.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node hplc.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node nut.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node chl.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node cruise_track.js >> API2Testing.log 
>> API2Testing.log echo.
cmd /c node upload.js >> API2Testing.log 









