run-server:
	bash ./bin/run-server.sh

run-client:
	bash ./bin/run-client.sh

build-mac-app:
	cd client && pyinstaller cheat-buster.spec

build-mac-sign: build-mac-app
	codesign --deep --force --sign - client/dist/cheat-buster.app

build-mac-dmg: build-mac-sign
	create-dmg \
	  --volname "Cheat Buster" \
	  --window-size 600 400 \
	  --icon-size 100 \
	  --icon "cheat-buster.app" 150 200 \
	  --app-drop-link 450 200 \
	  client/dist/Cheat-Buster.dmg \
	  client/dist/cheat-buster.app