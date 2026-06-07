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

build-windows-exe:
	python -c "from PIL import Image; img = Image.open('client/app/resources/logo.png').convert('RGBA'); img.save('client/app/resources/logo.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
	cd client && pyinstaller cheat-buster-windows.spec