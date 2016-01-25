version 6.0
if &cp | set nocp | endif
nnoremap <silent>  :nohlsearch=has('diff')?'|diffupdate':''
vmap [% [%m'gv``
vmap ]% ]%m'gv``
vmap a% [%v]%
let s:cpo_save=&cpo
set cpo&vim
nmap gx <Plug>NetrwBrowseX
nmap zuz <Plug>(FastFoldUpdate)
nnoremap <silent> <Plug>NetrwBrowseX :call netrw#NetrwBrowseX(expand("<cWORD>"),0)
nnoremap <silent> <Plug>(FastFoldUpdate) :FastFoldUpdate!
inoremap  u
let &cpo=s:cpo_save
unlet s:cpo_save
set autoindent
set autoread
set background=dark
set backspace=indent,eol,start
set complete=.,w,b,u,t
set display=lastline
set expandtab
set fileencodings=ucs-bom,utf-8,latin1
set fileformats=unix,dos,mac
set formatoptions=tcqlj
set guicursor=n-v-c:block,o:hor50,i-ci:hor15,r-cr:hor30,sm:block,a:blinkon0
set helplang=en
set history=1000
set hlsearch
set incsearch
set laststatus=2
set listchars=tab:»·,trail:·
set nrformats=hex
set ruler
set runtimepath=~/.vim,~/.vim/bundle/FastFold,~/.vim/bundle/SimpylFold,~/.vim/bundle/vim-colors-solarized,~/.vim/bundle/vim-flake8,~/.vim/bundle/vim-go,~/.vim/bundle/vim-pathogen,~/.vim/bundle/vim-python-pep8-indent,~/.vim/bundle/vim-sensible,/usr/share/vim/vimfiles,/usr/share/vim/vim74,/usr/share/vim/vimfiles/after,~/.vim/after
set scrolloff=1
set sessionoptions=blank,buffers,curdir,folds,help,tabpages,winsize
set shiftwidth=4
set showcmd
set sidescrolloff=5
set smarttab
set softtabstop=4
set tabpagemax=50
set tags=./tags;,./TAGS,tags,TAGS
set textwidth=78
set ttimeout
set ttimeoutlen=100
set viminfo=!,'20,\"50
set wildmenu
" vim: set ft=vim :
