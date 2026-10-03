Output demo.gif
Output demo.mp4
Source appearance.tape
Hide
Type "bash layout.sh"
Enter
Sleep 2s
Show
Sleep 1s
Type "dmon run --name quick python -u service.py quick"
Enter
Sleep 2s
Type "dmon stop --all"
Enter
Sleep 1s
Type "dmon start api"
Enter
Sleep 2s
Type "dmon status api"
Enter
Sleep 2s
Type "dmon exec worker"
Enter
Sleep 3s
Ctrl+C
Sleep 500ms
Type "dmon stop api"
Enter
Sleep 2s
Hide
