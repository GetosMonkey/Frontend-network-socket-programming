This is going to be the gui of our project

### navigation: 

cd "OneDrive - University of Cape Town\2026 Third Year\First Semester\CSC3002\Assignment 1 - Frontend"

### view tree: 

tree /f /a | Select-String -NotMatch "node_modules" | Select-String -NotMatch "   [|]"

Get-ChildItem -Recurse -Attributes !Directory+!Hidden | Where-Object { $_.FullName -notmatch 'node_modules' } | Select-Object FullName

# Running program: 

Terminal 1: The Core Backend Server
This runs your original tcp_server.py and the UDP status server.Terminal 2: The Antigravity Bridge (Sidecar Service).This runs the new client_service.py monkey-patch adapter that hosts the Socket.IO server on Port 5001 for your frontend to communicate with. Terminal 3: The Vite (React) Frontend. Open a new terminal at the root of your project (Assignment 1 - Frontend) where your package.json and tsconfig.app.json are located, and start the development server:

1) cd "OneDrive - University of Cape Town\2026 Third Year\First Semester\CSC3002\Assignment 1 - Frontend"
cd core
python server/tcp_server.py

2) cd "OneDrive - University of Cape Town\2026 Third Year\First Semester\CSC3002\Assignment 1 - Frontend"
cd core
python client_service.py

3) cd "OneDrive - University of Cape Town\2026 Third Year\First Semester\CSC3002\Assignment 1 - Frontend"
npm run dev

4) taskkill /F /IM python.exe
