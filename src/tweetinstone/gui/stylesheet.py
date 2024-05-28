# Custom style to give a twitter-esque look
# Reference: https://doc.qt.io/qtforpython-6/overviews/stylesheet-examples.html
# TODO FUTURE: different slightly-lighter mode as an option
# TODO FUTURE: fix coloring on the file menu
stylesheet='''
		QMainWindow{
			color: rgb(255, 255, 255); 
			background-color: black; 
			border: 1px solid rgb(47, 51, 54);
		}
		QPushButton{
			color: rgb(255, 255, 255);
			background-color: rgb(29, 155, 240);
			font-weight: bold;
			font-size: 16px;
			border-radius: 21px;
			padding-left: 16px;
			padding-right: 16px;
			padding: 12px;
		}
		QPushButton:disabled{
			color: #7f7f7f;
			background-color: #0e4d78;
		}
		QPushButton:pressed{
			color: #7f7f7f;
			background-color: #0e4d78;
		}
		QRadioButton:disabled{
			color: rgb(255, 255, 255);
		}
		QRadioButton:selected{
			color: rgb(255, 255, 255);
		}
		QGroupBox{
			color: rgb(255, 255, 255);
			font-weight: bold;
			font-size: 16px;
		}
		QDialog{
			color: rgb(255, 255, 255);
			background-color: black;
			border: 1px solid rgb(47, 51, 54);
		}
		QLabel{
			color: rgb(255, 255, 255);
		}
		QMenuBar{
			/* TODO FUTURE Fix this */
			color: rgb(255, 255, 255);
			background-color: black;
			border: 1px solid #16181c;
		}
		QMenuBar::item { /* FIX */
			color: rgb(255, 255, 255);
			background-color: black;
			padding: 1px 4px;
			background: transparent;
			border-radius: 4px;
		}
		QMenuBar:item:selected { /* when selected using mouse or keyboard */
			background: #0e4d78;
		}
		QMenuBar:item:pressed {
			background: rgb(29, 155, 240);
		}
		QMenu {
			background-color: #16181c; /* sets background of the menu */
			border: 1px solid black;
		}
		QMenu::item {
			/* sets background of menu item. set this to something non-transparent if you want menu color and menu item color to be different */
			background-color: transparent;
			color: rgb(255, 255, 255);
		}
		QMenu::item:selected { /* when user selects item using mouse or keyboard */
			background-color: #0e4d78;
		}
		QMenu::item:pressed { /* when user selects item using mouse or keyboard */
			background-color: rgb(29, 155, 240);
		}
		QMenu::item:disabled { /* when user selects item using mouse or keyboard */
			color: #7f7f7f;
		}
		QLineEdit{
			color: rgb(255, 255, 255);
			background-color: rgb(50, 50, 50);
		}
		/*QGroupBox {
			border: 2px solid gray
		}*/
		/* TODO FUTURE https://doc.qt.io/qtforpython-6/overviews/stylesheet-examples.html#customizing-qradiobutton */
		QRadioButton {
			color: rgb(255, 255, 255);
		}
		QRadioButton:disabled {
			color: #7f7f7f;
		}
		QRadioButton::indicator {
			width: 16px;
			height: 16px;
			color: rgb(29, 155, 240);
			background-color: rgb(29, 155, 240);
			border: 1px solid #0e4d78;
			border-radius: 8px;
		}
		QRadioButton:indicator:disabled {
			background-color: #16181c;
			border: 1px solid rgb(30, 30, 30);
		}
		QRadioButton:indicator:enabled:unchecked {
			background-color: #0e4d78
		}
		QRadioButton::indicator:unchecked:hover {
			background-color: rgb(29, 155, 240);
		}
		QRadioButton::indicator:unchecked:pressed {
			background-color: rgb(29, 155, 240);
		}
		QRadioButton::indicator:checked {
			background-color: rgb(29, 155, 240);
		}
		QRadioButton::indicator:checked:hover {
			background-color: rgb(29, 155, 240);
		}
		QRadioButton::indicator:checked:pressed {
			color: rgb(29, 155, 240);
			background-color: #0e4d78
		}
		QProgressBar{
			background-color: #0e4d78;
			border: 5px solid #0e4d78;
			border-radius: 14px;
			color: rgb(255, 255, 255);
			text-align: center;
			font-weight: bold;
			font-size: 14px;
		}
		QProgressBar::chunk{
			background-color: rgb(29, 155, 240);
			border-radius: 9px
		}
		/* TODO FUTURE FIX THIS */
		QInputDialog{
			width: 600px;
		}
		'''