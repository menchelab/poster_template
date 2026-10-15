$pdf_mode = 4;
$bibtex_use = 2;

push @extra_pdflatex_options, '-synctex=1' ;
$pdflatex = 'lualatex -shell-escape -file-line-error -synctex=1 %O %S';

@default_files = ('poster_template.tex');

$clean_ext = "ps aux blg fdb_latexmk fls nav out snm pdf synctex.gz";
