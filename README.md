# BDF Font to C Array Converter

This is a simple Python program meant to convert glyphs from BDF (Bitmap Distribution Format) font file into a C array. 

Main purpose of this program is generation of fonts for 128x64 OLED displays. 

Workflow is semi-manual, no console interface has been made. Settings must be adjusted by user in code. 

## Features

- Output is a sorted C array of structs with comments
- Characters have UTF-16 encoding
- Elements of array can be 1-4 byte values
- Support for large multi-row glyphs, in row-major or column-major draw order
- Configurable padding/trimming, rotation/mirroring

## Requirements

- Python 3.10+
- bdfparser Python library (can be installed from requirments.txt)

## Installation

1. Clone the repository

   ```bash
   git clone https://github.com/yourusername/bdf-to-c-array.git
   cd bdf-to-c-array
   ```

2. Create virtual environment

    Windows
    ```
    python -m venv .venv
    ```

    Linux, MacOS
    ```
    python3 -m venv .venv
    ```

3. Activate virtual environment

    Windows
    ```
    .venv/Scripts/activate.ps1
    ```

    Linux, MacOS
    ```
    source .venv/bin/activate
    ```
    Note: on Windows, execution of script in PowerShell might be blocked due to execution policy. Run following command to fix:
    ```
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
    ```

4. Install dependencies

    ```
    pip install -r requirements.txt
    ```

## Usage

To run program: activate virtual environment, run "main.py".  

Configuration is done by manually adjusting code. See code in "main.py" for details.

## Additional information

- https://github.com/Matiasus/SSD1306/tree/v3.x.x - lightweight SSD1306 driver library used to display font in hardware
- https://gitlab.freedesktop.org/xorg/font - collection of BDF fonts


## Contributing

Feel free to contribute via a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.

## Contact

If you have any questions or suggestions, feel free to open an issue or contact me at [your_email@example.com].