# JRC ISIA Poster Template
[![img](https://img.shields.io/badge/download-pdf-green)](https://git.isia.fh-salzburg.ac.at/publications/templates/isia-poster-template/-/jobs/artifacts/main/raw/poster_template.pdf?job=build_pdf)

This template is based on the Gemini modern LaTeX [beamerposter] theme. It can be used in portrait and landscape.


<p align="center">
<a href="https://raw.githubusercontent.com/anishathalye/assets/master/gemini/poster-gemini.pdf">
<img src="https://raw.githubusercontent.com/anishathalye/assets/master/gemini/poster-gemini-small.png">
</a>
</p>

If you're looking for a beamer presentation theme, take a look at [Auriga].

## Dependencies

* A TeX installation that includes [LuaTeX]
    * You also need `latexmk` if you want to use the provided `Makefile`
* LaTeX package dependencies including beamerposter (these usually come with
  your TeX installation, but if not, you can get them from [CTAN])
* [Raleway] and [Lato], which are both available under Open Font License

## Usage

1. Copy the files in this repository (or clone the repository)
1. In `poster_template.tex`, set up your paper size, column layout, and scale the
   content as necessary
1. Make a copy of `beamercolorthemegemini.sty`, update the `\usecolortheme`
   line in `poster_template.tex`, and theme the poster to your liking (optional, but
   highly recommended)
1. Run `latexmk` to build your poster

## Internal Maintainer

- [Martin Uray](mailto:martin.uray@fh-salzburg.ac.at)


## Themes

Gemini currently includes three color themes:

* `gemini` (default)
* `mit`
* `labsix`

The alternative themes are intended to be inspiration for you to make your own
color theme. You're highly recommended to make your own color theme (it's
really easy!) or use the default Gemini theme.

### MIT theme

<p align="center">
<a href="https://raw.githubusercontent.com/anishathalye/assets/master/gemini/poster-mit.pdf">
<img src="https://raw.githubusercontent.com/anishathalye/assets/master/gemini/poster-mit-small.png">
</a>
</p>

### LabSix theme

<p align="center">
<a href="https://raw.githubusercontent.com/anishathalye/assets/master/gemini/poster-labsix.pdf">
<img src="https://raw.githubusercontent.com/anishathalye/assets/master/gemini/poster-labsix-small.png">
</a>
</p>

## Design goals

* **Minimal**: clean and easy to read, so that the emphasis is on the content
* **Batteries included**: works and looks good out of the box
* **Easy theming**: easy to create and use a new color theme

## Contributing

Contributions to Gemini such as bug reports, new themes, and new poster
components are greatly appreciated! Given the subjective nature of design,
you're encouraged to open an issue or pull request early to get feedback before
investing a lot of time in implementing a new feature.

## License

Copyright (c) 2018-2022 Anish Athalye. Released under the MIT License. See
[LICENSE.md][license] for details.

[beamerposter]: https://github.com/deselaers/latex-beamerposter
[Auriga]: https://github.com/anishathalye/auriga
[LuaTeX]: http://www.luatex.org/
[CTAN]: https://ctan.org/
[Raleway]: https://www.fontsquirrel.com/fonts/raleway
[Lato]: https://www.fontsquirrel.com/fonts/lato
[license]: LICENSE.md
[FAQ]: https://github.com/anishathalye/gemini/wiki/FAQ
