from browser.gui import GUI

if __name__ == "__main__":
    app = GUI()
    try:
        app.run()
    except KeyboardInterrupt:
        exit()
