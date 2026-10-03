Output demo.gif
Output demo.mp4
Source appearance.tape
Hide
Type "bash layout.sh"
Enter
Sleep 2s
Show
Sleep 1s
Type "dmon stack up -d dev"
Enter
Sleep 2s
Type "dmon stack list"
Enter
Sleep 2s
Type "# Stop one member; keep the API running"
Enter
Type "dmon stop worker"
Enter
Sleep 2s
Type "dmon stack repair dev worker"
Enter
Sleep 2s
Type "dmon stack list"
Enter
Sleep 2s
Type "dmon stack down dev"
Enter
Sleep 2s
Hide
