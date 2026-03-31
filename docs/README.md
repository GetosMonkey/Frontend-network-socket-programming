This is going to be the gui of our project

### navigation: 

cd "OneDrive - University of Cape Town\2026 Third Year\First Semester\CSC3002\Assignment 1 - Frontend"

### view tree: 

tree /f /a | Select-String -NotMatch "node_modules" | Select-String -NotMatch "   [|]"

Get-ChildItem -Recurse -Attributes !Directory+!Hidden | Where-Object { $_.FullName -notmatch 'node_modules' } | Select-Object FullName