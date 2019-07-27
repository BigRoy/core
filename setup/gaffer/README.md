### How to automatically install Avalon for Gaffer

Make sure the `setup/gaffer/startup` folder is on your `GAFFER_STARTUP_PATHS`.
This will make sure Gaffer trigger the initialization script in 
`setup/gaffer/startup/gui` as soon as the Gaffer UI has initialized.

*Note that currently it will likely not auto-install when Gaffer is launched
without UI because it runs as a `gui` script. The menu install and the avalon
install could be separated into their own startup scripts so avalon would also
install when running in batch mode (non-GUI).

More info, see:
- http://www.gafferhq.org/documentation/0.53.0.0/Tutorials/Scripting/AddingAMenuItem/index.html
- https://groups.google.com/forum/#!msg/gaffer-dev/TB7XBS9riGo/4I2O2czrEQAJ